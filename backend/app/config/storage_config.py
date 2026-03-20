"""
对象存储配置（S3 兼容：AWS S3 / MinIO / OSS S3 兼容网关等）。
"""
import os
from typing import Any


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

    return {
        "endpoint": endpoint,
        "access_key": access_key,
        "secret_key": secret_key,
        "bucket": bucket,
        "region": region,
        "public_base_url": public_base_url,
        "force_path_style": force_path_style,
        "enabled": bool(access_key and secret_key and bucket),
    }
