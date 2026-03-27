"""
简单调试端点 - 检查TIKHUB环境变量
"""
import os
from fastapi import APIRouter
from app.services import tikhub_client

router = APIRouter()

@router.get("/debug/tikhub-env")
def check_tikhub_env():
    """检查TIKHUB_API_KEY是否可用"""
    key = os.environ.get("TIKHUB_API_KEY", "")
    
    return {
        "has_key": bool(key),
        "key_length": len(key),
        "key_first_5": key[:5] + "..." if key else "empty",
    }

@router.get("/debug/tikhub-status")
def check_tikhub_status():
    """检查tikhub_client.is_configured()"""
    return {
        "is_configured": tikhub_client.is_configured(),
        "key_from_client": bool(os.environ.get("TIKHUB_API_KEY", "").strip()),
    }