"""手机号验证码：发码、校验、注册/登录。"""

from __future__ import annotations

import hashlib
import os
import random
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import AuthOtp, User
from app.services.jwt_tokens import mint_access_token
from app.services.sms_provider import send_login_verification_code

_CN_PHONE = re.compile(r"^1[3-9]\d{9}$")

OTP_TTL_SEC = int(os.environ.get("OTP_TTL_SEC", "300"))
OTP_RESEND_SEC = int(os.environ.get("OTP_RESEND_SEC", "60"))
OTP_BYPASS_ENABLED = os.environ.get("OTP_BYPASS_ENABLED", "").strip().lower() in (
    "1",
    "true",
    "yes",
)
OTP_BYPASS_CODE = os.environ.get("OTP_BYPASS_CODE", "123456").strip() or "123456"


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
    # 临时免短信模式：用于短信通道未开通时的联调/压测。
    if OTP_BYPASS_ENABLED and code.strip() == OTP_BYPASS_CODE:
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
    return mint_access_token(user.user_id, user.phone)
