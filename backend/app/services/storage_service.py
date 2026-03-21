"""
对象存储服务：上传、下载、URL 生成。
支持 S3 兼容存储；未配置时自动使用本地文件系统（便于本地开发）。
S3 上传失败时（凭证/网络/权限）在未设置 STORAGE_LOCAL_DISABLED 时可回退到本地磁盘。
"""
import logging
import uuid
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config

from app.config.storage_config import get_storage_config

# 本地存储的 bucket 标识
LOCAL_BUCKET = "local"

logger = logging.getLogger(__name__)


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
    # SigV4；addressing_style：OSS/AWS 需 virtual-hosted（见 storage_config._default_force_path_style）
    kwargs["config"] = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path" if cfg.get("force_path_style") else "virtual"},
    )
    return boto3.client("s3", **kwargs)


def _upload_bytes_local(
    ip_id: str,
    file_name: str,
    content_type: str | None,
    data: bytes,
    *,
    force: bool = False,
) -> dict[str, Any] | None:
    """
    本地文件存储上传。
    force=False：仅在「未配置 S3、走本地主路径」时可用（local_enabled）。
    force=True：S3 失败后的回退，只要未设置 STORAGE_LOCAL_DISABLED 即可写盘。
    """
    cfg = get_storage_config()
    if cfg.get("local_disabled"):
        return None
    if not force and not cfg.get("local_enabled"):
        return None
    base = Path(cfg["local_path"])
    ext = Path(file_name or "").suffix
    file_id = f"file_{uuid.uuid4().hex[:20]}"
    object_key = f"ip/{ip_id}/{file_id}{ext}"
    full_path = base / object_key
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
    except OSError as e:
        logger.warning("Local disk upload failed: %s", e)
        return None
    return {
        "file_id": file_id,
        "bucket": LOCAL_BUCKET,
        "object_key": object_key,
        "size_bytes": len(data),
        "content_type": content_type,
    }


def upload_bytes(ip_id: str, file_name: str, content_type: str | None, data: bytes) -> dict[str, Any] | None:
    cfg = get_storage_config()
    # 优先 S3（含客户端创建、put_object 任一步失败则回退本地，避免未捕获异常导致 500）
    if cfg.get("s3_enabled"):
        try:
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
            logger.warning("S3 已配置但 client 或 bucket 不可用，尝试本地回退")
        except Exception as e:
            logger.warning("S3 上传失败，尝试本地回退: %s", e)
        fallback = _upload_bytes_local(ip_id, file_name, content_type, data, force=True)
        if fallback:
            return fallback
        return None
    # 未配置 S3：仅本地主路径
    return _upload_bytes_local(ip_id, file_name, content_type, data, force=False)


def download_bytes(bucket: str, object_key: str) -> bytes | None:
    cfg = get_storage_config()
    # 本地盘上的对象（含「配置了 S3 但回退写入」的情况，此时 local_enabled 可能为 False）
    if bucket == LOCAL_BUCKET:
        if cfg.get("local_disabled"):
            return None
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
