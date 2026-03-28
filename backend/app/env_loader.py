"""
从 backend/.env 加载环境变量，路径固定为「本文件所在仓库的 backend 目录」，
不依赖 uvicorn / 脚本的当前工作目录。
"""
from pathlib import Path

from dotenv import load_dotenv

# backend/app/env_loader.py -> parent.parent == backend/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent


def load_backend_env() -> None:
    load_dotenv(_BACKEND_ROOT / ".env")
