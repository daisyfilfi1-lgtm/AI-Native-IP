"""
对象存储配置（S3 兼容：AWS S3 / MinIO / OSS S3 兼容网关等）。
未配置 S3 时，可启用本地文件存储作为 fallback，便于本地开发。
"""
import os
from pathlib import Path
from typing import Any

# 本地存储默认目录
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_LOCAL_PATH = _BACKEND_ROOT / "data" / "uploads"

# Railway 环境使用 /tmp（可写）
def _get_default_local_path() -> Path:
    if os.getenv("RAILWAY_ENVIRONMENT"):
        # Railway 使用 /tmp，因为其他目录可能只读
        return Path("/tmp/ip_uploads")
    return _DEFAULT_LOCAL_PATH


def _default_force_path_style(endpoint: str | None) -> bool:
    if not endpoint:
        return True
    e = endpoint.lower()
    if "aliyuncs.com" in e or "aliyuncs.com.cn" in e:
        return False
    if "amazonaws.com" in e:
        return False
    return True


def get_storage_config() -> dict[str, Any]:
    endpoint = os.environ.get("STORAGE_ENDPOINT", "").strip() or None
    access_key = os.environ.get("STORAGE_ACCESS_KEY", "").strip() or None
    secret_key = os.environ.get("STORAGE_SECRET_KEY", "").strip() or None
    bucket = os.environ.get("STORAGE_BUCKET", "").strip() or None
    region = os.environ.get("STORAGE_REGION", "").strip() or None
    public_base_url = os.environ.get("STORAGE_PUBLIC_BASE_URL", "").strip() or None
    
    raw_style = os.environ.get("STORAGE_FORCE_PATH_STYLE", "").strip()
    if raw_style:
        force_path_style = raw_style.lower() in ("true", "1", "yes")
    else:
        force_path_style = _default_force_path_style(endpoint)
    
    s3_enabled = bool(access_key and secret_key and bucket)
    
    # 本地存储路径
    local_path_env = os.environ.get("STORAGE_LOCAL_PATH", "").strip()
    if local_path_env:
        local_path = Path(local_path_env)
    else:
        local_path = _get_default_local_path()
    
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
        "local_disabled": local_disabled,
        "local_path": str(local_path),
    }
