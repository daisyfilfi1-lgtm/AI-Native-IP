"""
API 密钥验证中间件
提供基础的访问控制，防止未授权访问
"""
import os
from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

# 从环境变量读取 API 密钥
API_KEY = os.environ.get("API_KEY", "").strip()
IS_PRODUCTION = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"

# 开发环境默认密钥（仅用于测试）
DEFAULT_DEV_KEY = "dev-key-do-not-use-in-production"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(request: Request, api_key: str = Security(api_key_header)):
    """
    验证 API 密钥
    - 生产环境：必须提供正确的密钥
    - 开发环境：允许使用默认密钥或跳过
    """
    # 某些路径可以公开访问
    public_paths = ["/health", "/docs", "/openapi.json", "/"]
    if any(request.url.path.startswith(p) for p in public_paths):
        return True
    
    # 生产环境必须配置 API_KEY
    if IS_PRODUCTION:
        if not API_KEY:
            raise HTTPException(
                status_code=500,
                detail="Server misconfiguration: API_KEY not set"
            )
        if api_key != API_KEY:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key"
            )
        return True
    
    # 开发环境：宽松验证
    effective_key = API_KEY or DEFAULT_DEV_KEY
    if api_key and api_key != effective_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return True


def require_api_key():
    """依赖项注入用"""
    return Security(verify_api_key)
