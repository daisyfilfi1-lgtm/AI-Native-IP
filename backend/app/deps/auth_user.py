"""从 Bearer JWT 解析当前登录用户。"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User
from app.services.jwt_tokens import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="无效或已过期的令牌")
    uid = str(payload["sub"])
    user = db.query(User).filter(User.user_id == uid).first()
    if user:
        return user
    # 非生产：联调时可能使用无库 OTP bypass，JWT 内已有 phone，用内存 User 放行
    if os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production":
        raise HTTPException(status_code=401, detail="用户不存在")
    phone = payload.get("phone")
    if isinstance(phone, str) and phone.strip():
        now = datetime.utcnow()
        return User(
            user_id=uid,
            phone=phone.strip(),
            created_at=now,
            updated_at=now,
            last_login_at=now,
        )
    raise HTTPException(status_code=401, detail="用户不存在")
