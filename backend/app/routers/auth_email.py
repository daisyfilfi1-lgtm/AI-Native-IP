"""
邮箱/手机号 + 密码登录
"""
from __future__ import annotations

import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User

router = APIRouter()


def _hash_password(password: str) -> str:
    """简单密码哈希 (生产环境建议用bcrypt)"""
    return hashlib.sha256(password.encode()).hexdigest()


class RegisterBody(BaseModel):
    email: str = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=50)
    phone: str = Field(None, description="手机号(可选)")


class LoginBody(BaseModel):
    email: str = Field(..., description="邮箱")
    password: str = Field(..., description="密码")


@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    """注册新用户"""
    # 检查邮箱是否已存在
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    # 创建用户
    user = User(
        user_id=f"u_{hashlib.sha256(body.email.encode()).hexdigest()[:16]}",
        email=body.email,
        password_hash=_hash_password(body.password),
        phone=body.phone,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    
    return {"ok": True, "message": "注册成功"}


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    """密码登录"""
    # 查找用户
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 验证密码
    if user.password_hash != _hash_password(body.password):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # 生成简单token (生产环境建议用JWT)
    token = f"tok_{user.user_id}_{datetime.utcnow().timestamp()}"
    
    return {
        "token": token,
        "user": {
            "userId": user.user_id,
            "email": user.email,
            "phone": user.phone,
        }
    }


# 迁移旧手机号用户 (可选)
@router.post("/migrate-phone-user")
def migrate_phone_user(
    phone: str,
    password: str,
    db: Session = Depends(get_db)
):
    """为已有手机号用户设置密码"""
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.password_hash = _hash_password(password)
    user.email = f"{phone}@local"
    db.commit()
    
    return {"ok": True, "message": "密码已设置"}