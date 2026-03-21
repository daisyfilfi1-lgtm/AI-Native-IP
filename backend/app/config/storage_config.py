"""
对象存储配置（S3 兼容：AWS S3 / MinIO / OSS S3 兼容网关等）。
未配置 S3 时，可启用本地文件存储作为 fallback，便于本地开发。
"""
import os
from pathlib import Path
from typing import Any

# 本地存储默认目录（backend/data/uploads）
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_LOCAL_PATH = _BACKEND_ROOT / "data" / "uploads"


def get_storage_config() -> dict[str, Any]:
    endpoint = os.environ.get("STORAGE_ENDPOINT", "").strip() or None
    access_key = os.environ.get("STORAGE_ACCESS_KEY", "").strip() or None
    secret_key = os.environ.get("STORAGE_SECRET_KEY", "").strip() or None
    bucket = os.environ.get("STORAGE_BUCKET", "").strip() or None
    region = os.environ.get("STORAGE_REGION", "").strip() or None
    public_base_url = os.environ.get("STORAGE_PUBLIC_BASE_URL", "").strip() or None
    force_path_style = os.environ.get("STORAGE_FORCE_PATH_STYLE", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    s3_enabled = bool(access_key and secret_key and bucket)

    # 本地存储：S3 未配置时默认启用，用于本地开发
    local_path_env = os.environ.get("STORAGE_LOCAL_PATH", "").strip()
    local_path = Path(local_path_env) if local_path_env else _DEFAULT_LOCAL_PATH
    local_disabled = os.environ.get("STORAGE_LOCAL_DISABLED", "").lower() in ("true", "1", "yes")
    use_local = not s3_enabled and not local_disabled

    return {
        "endpoint": endpoint,
        "access_key": access_key,
        "secret_key": secret_key,
        "bucket": bucket,
        "region": region,
        "public_base_url": public_base_url,
        "force_path_style": force_path_style,
        "enabled": s3_enabled or use_local,
        "s3_enabled": s3_enabled,
        "local_enabled": use_local,
        "local_path": str(local_path.resolve()),
    }
