"""
对象存储服务：上传、下载、URL 生成。
支持 S3 兼容存储；未配置时自动使用本地文件系统（便于本地开发）。
"""
import uuid
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config

from app.config.storage_config import get_storage_config

# 本地存储的 bucket 标识
LOCAL_BUCKET = "local"


def _get_s3_client() -> Any | None:
    cfg = get_storage_config()
    if not cfg.get("enabled"):
        return None
    kwargs: dict[str, Any] = {
        "aws_access_key_id": cfg["access_key"],
        "aws_secret_access_key": cfg["secret_key"],
    }
    if cfg.get("region"):
        kwargs["region_name"] = cfg["region"]
    if cfg.get("endpoint"):
        kwargs["endpoint_url"] = cfg["endpoint"]
    # 阿里云 OSS 等 S3 兼容端点通常要求 SigV4；未显式配置时与 AWS 行为一致
    kwargs["config"] = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path" if cfg.get("force_path_style") else "virtual"},
    )
    return boto3.client("s3", **kwargs)


def _upload_bytes_local(ip_id: str, file_name: str, content_type: str | None, data: bytes) -> dict[str, Any] | None:
    """本地文件存储上传（S3 未配置时使用）"""
    cfg = get_storage_config()
    if not cfg.get("local_enabled"):
        return None
    base = Path(cfg["local_path"])
    ext = Path(file_name or "").suffix
    file_id = f"file_{uuid.uuid4().hex[:20]}"
    object_key = f"ip/{ip_id}/{file_id}{ext}"
    full_path = base / object_key
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)
    return {
        "file_id": file_id,
        "bucket": LOCAL_BUCKET,
        "object_key": object_key,
        "size_bytes": len(data),
        "content_type": content_type,
    }


def upload_bytes(ip_id: str, file_name: str, content_type: str | None, data: bytes) -> dict[str, Any] | None:
    cfg = get_storage_config()
    # 优先 S3
    if cfg.get("s3_enabled"):
        client = _get_s3_client()
        bucket = cfg.get("bucket")
        if client and bucket:
            ext = Path(file_name or "").suffix
            file_id = f"file_{uuid.uuid4().hex[:20]}"
            object_key = f"ip/{ip_id}/{file_id}{ext}"
            extra_args: dict[str, Any] = {}
            if content_type:
                extra_args["ContentType"] = content_type
            client.put_object(Bucket=bucket, Key=object_key, Body=data, **extra_args)
            return {
                "file_id": file_id,
                "bucket": bucket,
                "object_key": object_key,
                "size_bytes": len(data),
                "content_type": content_type,
            }
    # S3 不可用时 fallback 本地
    return _upload_bytes_local(ip_id, file_name, content_type, data)


def download_bytes(bucket: str, object_key: str) -> bytes | None:
    cfg = get_storage_config()
    if bucket == LOCAL_BUCKET and cfg.get("local_enabled"):
        full_path = Path(cfg["local_path"]) / object_key
        if full_path.exists():
            return full_path.read_bytes()
        return None
    client = _get_s3_client()
    if not client:
        return None
    try:
        resp = client.get_object(Bucket=bucket, Key=object_key)
        body = resp.get("Body")
        return body.read() if body else None
    except Exception:
        return None


def build_public_url(bucket: str, object_key: str) -> str:
    if bucket == LOCAL_BUCKET:
        return f"file://{Path(get_storage_config()['local_path']) / object_key}"
    cfg = get_storage_config()
    base = cfg.get("public_base_url")
    if base:
        return f"{base.rstrip('/')}/{object_key.lstrip('/')}"
    endpoint = cfg.get("endpoint")
    if endpoint:
        return f"{endpoint.rstrip('/')}/{bucket}/{object_key}"
    return f"s3://{bucket}/{object_key}"
