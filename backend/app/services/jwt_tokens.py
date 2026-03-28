"""JWT access tokens for phone login."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import jwt

JWT_ALGORITHM = "HS256"


def _jwt_secret() -> str:
    s = os.environ.get("JWT_SECRET", "").strip()
    if s:
        return s
    if os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production":
        raise RuntimeError("JWT_SECRET must be set in production")
    return "dev-only-jwt-secret-do-not-use-in-production"


def mint_access_token(
    user_id: str,
    phone: str,
    email: Optional[str] = None,
) -> str:
    exp_sec = int(os.environ.get("JWT_EXPIRE_SEC", str(7 * 24 * 3600)))
    now = int(time.time())
    payload: Dict[str, Any] = {
        "sub": user_id,
        "phone": phone,
        "iat": now,
        "exp": now + exp_sec,
    }
    if email and str(email).strip():
        payload["email"] = str(email).strip()
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码失败返回 None。生产环境若未配置 JWT_SECRET，_jwt_secret() 可能抛错，须捕获以免鉴权中间件 500。
    """
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None
