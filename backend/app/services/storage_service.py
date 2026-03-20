"""
对象存储服务：上传、下载、URL 生成。
"""
import uuid
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config

from app.config.storage_config import get_storage_config


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


def upload_bytes(ip_id: str, file_name: str, content_type: str | None, data: bytes) -> dict[str, Any] | None:
    client = _get_s3_client()
    cfg = get_storage_config()
    if not client or not cfg.get("bucket"):
        return None

    ext = Path(file_name or "").suffix
    file_id = f"file_{uuid.uuid4().hex[:20]}"
    object_key = f"ip/{ip_id}/{file_id}{ext}"
    extra_args: dict[str, Any] = {}
    if content_type:
        extra_args["ContentType"] = content_type

    client.put_object(Bucket=cfg["bucket"], Key=object_key, Body=data, **extra_args)

    return {
        "file_id": file_id,
        "bucket": cfg["bucket"],
        "object_key": object_key,
        "size_bytes": len(data),
        "content_type": content_type,
    }


def download_bytes(bucket: str, object_key: str) -> bytes | None:
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
    cfg = get_storage_config()
    base = cfg.get("public_base_url")
    if base:
        return f"{base.rstrip('/')}/{object_key.lstrip('/')}"
    endpoint = cfg.get("endpoint")
    if endpoint:
        return f"{endpoint.rstrip('/')}/{bucket}/{object_key}"
    return f"s3://{bucket}/{object_key}"
