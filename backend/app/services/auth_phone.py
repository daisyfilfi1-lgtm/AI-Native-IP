"""手机号验证码：发码、校验、注册/登录。"""

from __future__ import annotations

import hashlib
import logging
import os
import random
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.models import AuthOtp, User

logger = logging.getLogger(__name__)
from app.services.jwt_tokens import mint_access_token
from app.services.sms_provider import send_login_verification_code

_CN_PHONE = re.compile(r"^1[3-9]\d{9}$")

OTP_TTL_SEC = int(os.environ.get("OTP_TTL_SEC", "300"))
OTP_RESEND_SEC = int(os.environ.get("OTP_RESEND_SEC", "60"))


def _otp_bypass_enabled() -> bool:
    """
    运行时读取免短信开关，避免进程启动后环境变量变更不生效。
    兼容：当未显式配置 OTP_BYPASS_ENABLED 且 SMS_PROVIDER=mock 时，默认允许联调免短信登录。
    """
    raw = os.environ.get("OTP_BYPASS_ENABLED")
    if raw is not None and str(raw).strip() != "":
        return str(raw).strip().lower() in ("1", "true", "yes")
    return os.environ.get("SMS_PROVIDER", "mock").strip().lower() == "mock"


def _otp_bypass_code() -> str:
    return os.environ.get("OTP_BYPASS_CODE", "123456").strip() or "123456"


def _is_production_deploy() -> bool:
    return os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"


def accept_any_login() -> bool:
    """
    「任意手机号 + 任意验证码」联调模式（含 Railway 上给客户演示 / UAT）。

    必须**显式**设置环境变量 AUTH_ACCEPT_ANY_LOGIN=1|true|yes 才开启；未设置默认为关闭。
    在 production 上开启时会打 warning 日志，测试结束后务必关掉。
    """
    raw = os.environ.get("AUTH_ACCEPT_ANY_LOGIN", "").strip().lower()
    if raw not in ("1", "true", "yes"):
        return False
    if _is_production_deploy():
        logger.warning(
            "AUTH_ACCEPT_ANY_LOGIN is enabled while RAILWAY_ENVIRONMENT_NAME=production — "
            "customer UAT/demo only; set AUTH_ACCEPT_ANY_LOGIN=false after testing"
        )
    return True


def resolve_login_phone_for_dev_any(raw: str) -> str:
    """
    将任意输入映射为合法 11 位大陆手机号（联调时可乱填）。
    空输入使用固定测试号。
    """
    if not raw or not str(raw).strip():
        return "18600000000"
    p = normalize_phone(raw)
    if p:
        return p
    seed = hashlib.sha256(str(raw).strip().encode("utf-8")).hexdigest()
    second = 3 + int(seed[:2], 16) % 7
    tail = "".join(str(int(seed[i : i + 2], 16) % 10) for i in range(2, 20, 2))[:9]
    return f"1{second}{tail.ljust(9, '0')[:9]}"


def _login_or_upsert_user_bypass(db: Session, phone: str) -> User:
    """联调免校验：写库或数据库不可用时返回内存 User。"""
    try:
        now = datetime.utcnow()
        user = db.query(User).filter(User.phone == phone).first()
        if not user:
            user = User(
                user_id=f"u_{uuid.uuid4().hex[:16]}",
                phone=phone,
                last_login_at=now,
            )
            db.add(user)
        else:
            user.last_login_at = now
            user.updated_at = now
        db.commit()
        db.refresh(user)
        return user
    except OperationalError as e:
        if _is_production_deploy():
            raise
        logger.warning(
            "OTP bypass: database unavailable (%s); using stateless user for local/dev",
            e,
        )
        return _synthetic_user_for_otp_bypass(phone)


def _synthetic_user_for_otp_bypass(phone: str) -> User:
    """数据库不可用时，非生产环境用稳定 user_id 生成内存中的 User（仅联调码）。"""
    uid = "u_" + hashlib.sha256(f"local-bypass:{phone}".encode()).hexdigest()[:16]
    now = datetime.utcnow()
    return User(
        user_id=uid,
        phone=phone,
        created_at=now,
        updated_at=now,
        last_login_at=now,
    )


def _pepper() -> bytes:
    return (os.environ.get("OTP_PEPPER") or os.environ.get("JWT_SECRET") or "dev-otp-pepper").encode(
        "utf-8"
    )


def hash_otp(phone: str, code: str) -> str:
    raw = f"{phone}:{code}".encode("utf-8")
    return hashlib.sha256(_pepper() + raw).hexdigest()


def normalize_phone(raw: str) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw.strip())
    if len(digits) == 11 and _CN_PHONE.match(digits):
        return digits
    return None


def generate_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def send_code(db: Session, phone: str) -> Tuple[bool, str]:
    """写入 OTP 并发短信。返回 (ok, message)。"""
    now = datetime.utcnow()
    recent = (
        db.query(AuthOtp)
        .filter(AuthOtp.phone == phone, AuthOtp.consumed.is_(False))
        .order_by(AuthOtp.created_at.desc())
        .first()
    )
    if recent and (now - recent.created_at).total_seconds() < OTP_RESEND_SEC:
        return False, f"请 {OTP_RESEND_SEC} 秒后再试"

    code = generate_code()
    row = AuthOtp(
        phone=phone,
        code_hash=hash_otp(phone, code),
        expires_at=now + timedelta(seconds=OTP_TTL_SEC),
        consumed=False,
    )
    db.add(row)
    db.commit()

    try:
        send_login_verification_code(phone, code)
    except Exception as e:
        db.delete(row)
        db.commit()
        return False, str(e)

    return True, "sent"


def verify_code_and_upsert_user(db: Session, phone: str, code: str) -> Optional[User]:
    """校验验证码，创建或更新用户，失败返回 None。"""
    # 联调：非生产下可跳过验证码校验（见 accept_any_login）
    if accept_any_login():
        return _login_or_upsert_user_bypass(db, phone)

    # 临时免短信模式：用于短信通道未开通时的联调/压测。
    if _otp_bypass_enabled() and code.strip() == _otp_bypass_code():
        return _login_or_upsert_user_bypass(db, phone)

    now = datetime.utcnow()
    rows = (
        db.query(AuthOtp)
        .filter(
            AuthOtp.phone == phone,
            AuthOtp.consumed.is_(False),
            AuthOtp.expires_at > now,
        )
        .order_by(AuthOtp.created_at.desc())
        .limit(5)
        .all()
    )
    expect = hash_otp(phone, code.strip())
    matched: Optional[AuthOtp] = None
    for r in rows:
        if r.code_hash == expect:
            matched = r
            break
    if not matched:
        return None

    matched.consumed = True
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        user = User(
            user_id=f"u_{uuid.uuid4().hex[:16]}",
            phone=phone,
            last_login_at=now,
        )
        db.add(user)
    else:
        user.last_login_at = now
        user.updated_at = now
    db.commit()
    db.refresh(user)
    return user


def issue_token_for_user(user: User) -> str:
    return mint_access_token(
        user.user_id,
        str(user.phone or ""),
        user.email if user.email else None,
    )
