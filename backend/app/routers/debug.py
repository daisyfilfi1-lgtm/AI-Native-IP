"""
简单调试端点 - 检查TIKHUB环境变量
"""
from fastapi import APIRouter
import os

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