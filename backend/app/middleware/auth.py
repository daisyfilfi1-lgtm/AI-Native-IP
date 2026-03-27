"""
API 访问控制：X-API-Key（服务间）或 Authorization: Bearer JWT（手机号登录用户）。
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.services.jwt_tokens import decode_access_token

API_KEY = os.environ.get("API_KEY", "").strip()
IS_PRODUCTION = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"
DEFAULT_DEV_KEY = "dev-key-do-not-use-in-production"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def _is_docs_or_health(path: str) -> bool:
    if path == "/":
        return True
    if path.startswith("/health"):
        return True
    if path.startswith("/docs") or path.startswith("/redoc") or path.startswith("/openapi.json"):
        return True
    return False


def _is_public_auth_route(path: str, method: str) -> bool:
    return (path, method.upper()) in (
        ("/api/auth/sms/send-code", "POST"),
        ("/api/auth/sms/login", "POST"),
        ("/api/auth/login", "POST"),
        ("/api/auth/register", "POST"),
    )


async def verify_api_key_or_jwt(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
):
    """
    - 文档与健康检查：无需鉴权
    - 发码/验证码登录：无需鉴权
    - 其它：有效 JWT **或** 有效 X-API-Key（开发环境可不传 key）
    """
    path = request.url.path
    method = request.method.upper()

    if _is_docs_or_health(path) or _is_public_auth_route(path, method):
        return True

    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("sub"):
            request.state.user_id = str(payload["sub"])
            request.state.user_phone = payload.get("phone")
            return True

    if IS_PRODUCTION:
        if not API_KEY:
            raise HTTPException(
                status_code=503,
                detail="Server misconfiguration: API_KEY not set",
            )
        if api_key != API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing credentials",
            )
        return True

    effective_key = API_KEY or DEFAULT_DEV_KEY
    if api_key and api_key != effective_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    return True


def require_api_key():
    return Security(verify_api_key_or_jwt)
