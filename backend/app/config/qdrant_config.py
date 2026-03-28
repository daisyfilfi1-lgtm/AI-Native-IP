"""
Qdrant 向量数据库配置
"""
import os
from typing import Any, Optional


def get_qdrant_config() -> dict[str, Any]:
    """
    返回 Qdrant 配置
    """
    return {
        "url": os.environ.get("QDRANT_URL", "http://localhost:6333").strip(),
        "api_key": os.environ.get("QDRANT_API_KEY", "").strip() or None,
        "timeout": int(os.environ.get("QDRANT_TIMEOUT", "30")),
        # 本地模式不需要api_key，云端需要
        "local_mode": os.environ.get("QDRANT_URL", "").startswith("http://localhost"),
    }


def is_qdrant_configured() -> bool:
    """检查Qdrant是否已配置"""
    config = get_qdrant_config()
    # 本地模式不需要api_key
    if config["local_mode"]:
        return True
    # 云端模式需要api_key
    return bool(config["api_key"])
