"""手机号 + 短信验证码注册与登录。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User
from app.deps.auth_user import get_current_user
from app.services import auth_phone

router = APIRouter()


class SendCodeBody(BaseModel):
    phone: str = Field(..., min_length=11, max_length=20)


class LoginBody(BaseModel):
    phone: str = Field(..., min_length=11, max_length=20)
    code: str | None = Field(default=None, max_length=10)
    password: str | None = Field(
        default=None,
        max_length=10,
        description="与 code 二选一；联调时填 OTP_BYPASS_CODE（默认 123456）",
    )


@router.post("/sms/send-code")
def send_code(body: SendCodeBody, db: Session = Depends(get_db)):
    """发送登录验证码（同一号码有发送间隔）。"""
    phone = auth_phone.normalize_phone(body.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="请输入有效的中国大陆手机号")
    ok, msg = auth_phone.send_code(db, phone)
    if not ok:
        raise HTTPException(status_code=429, detail=msg)
    return {"ok": True, "message": msg}


@router.post("/sms/login")
def login_with_code(body: LoginBody, db: Session = Depends(get_db)):
    """
    验证码登录（若手机号未注册则自动注册）。
    返回 JWT，请在后续请求头携带：Authorization: Bearer <token>
    """
    phone = auth_phone.normalize_phone(body.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="请输入有效的中国大陆手机号")
    raw_code = (body.code or body.password or "").strip()
    if len(raw_code) < 4:
        raise HTTPException(
            status_code=400,
            detail="请提供验证码 code，或联调密码字段 password（与 code 相同含义）",
        )
    user = auth_phone.verify_code_and_upsert_user(db, phone, raw_code)
    if not user:
        raise HTTPException(status_code=401, detail="验证码错误或已过期")
    token = auth_phone.issue_token_for_user(user)
    return {
        "token": token,
        "user": {"userId": user.user_id, "phone": user.phone},
    }


@router.get("/me")
def auth_me(user: User = Depends(get_current_user)):
    """当前登录用户信息（需 Bearer）。"""
    return {"userId": user.user_id, "phone": user.phone}
