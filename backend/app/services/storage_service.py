"""
对象存储服务：上传、下载、URL 生成。
支持 S3 兼容存储；未配置时自动使用本地文件系统（便于本地开发）。
S3 上传失败时（凭证/网络/权限）在未设置 STORAGE_LOCAL_DISABLED 时可回退到本地磁盘。

阿里云 OSS：新版 botocore 可能对 PutObject 使用 aws-chunked + 流式校验，OSS 会报错
「aws-chunked encoding is not supported with the specified x-amz-content-sha256」。
通过 Config（when_required + payload_signing）与单次 PUT + ContentMD5 避免分块流式上传。
"""
import base64
import hashlib
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config

from app.config.storage_config import get_storage_config

# 本地存储的 bucket 标识
LOCAL_BUCKET = "local"

logger = logging.getLogger(__name__)


def _content_md5_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.md5(data).digest()).decode("ascii")


def _is_safe_path(base: Path, target: Path) -> bool:
    """防止路径遍历攻击：确保 target 在 base 目录下"""
    try:
        # 使用 relative_to 检查是否在 base 下
        target.resolve().relative_to(base.resolve())
        return True
    except (ValueError, OSError, RuntimeError):
        return False


def _s3_connect_timeout_seconds() -> float:
    raw = os.environ.get("S3_CONNECT_TIMEOUT_SECONDS", "10").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 10.0


def _s3_read_timeout_seconds() -> float:
    """get_object / Body.read() 等读超时，避免 OSS 网络挂起导致录入永久 PROCESSING。"""
    raw = os.environ.get("S3_READ_TIMEOUT_SECONDS", "120").strip()
    try:
        return max(5.0, float(raw))
    except ValueError:
        return 120.0


def _s3_client_config(cfg: dict[str, Any]) -> Config:
    style = "path" if cfg.get("force_path_style") else "virtual"
    return Config(
        signature_version="s3v4",
        connect_timeout=_s3_connect_timeout_seconds(),
        read_timeout=_s3_read_timeout_seconds(),
        retries={"max_attempts": 3, "mode": "standard"},
        s3={
            "addressing_style": style,
            # 整包 SHA256 签名，避免默认走流式 chunked（OSS 不支持 aws-chunked + 部分 x-amz-content-sha256）
            "payload_signing_enabled": True,
        },
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
    )


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
    kwargs["config"] = _s3_client_config(cfg)
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
    
    try:
        base = Path(cfg["local_path"])
        ext = Path(file_name or "").suffix
        file_id = f"file_{uuid.uuid4().hex[:20]}"
        object_key = f"ip/{ip_id}/{file_id}{ext}"
        full_path = base / object_key
        
        # 安全检查
        if not _is_safe_path(base, full_path):
            logger.warning("Path traversal blocked: %s", object_key)
            return None
        
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        
        return {
            "file_id": file_id,
            "bucket": LOCAL_BUCKET,
            "object_key": object_key,
            "size_bytes": len(data),
            "content_type": content_type,
        }
    except OSError as e:
        logger.error("Local upload failed: %s", e)
        return None


def upload_bytes(ip_id: str, file_name: str, content_type: str | None, data: bytes) -> dict[str, Any] | None:
    """上传 bytes 数据（向后兼容）"""
    cfg = get_storage_config()
    
    if cfg.get("s3_enabled"):
        try:
            client = _get_s3_client()
            bucket = cfg.get("bucket")
            if client and bucket:
                ext = Path(file_name or "").suffix
                file_id = f"file_{uuid.uuid4().hex[:20]}"
                object_key = f"ip/{ip_id}/{file_id}{ext}"
                extra_args: dict[str, Any] = {
                    "ContentMD5": _content_md5_b64(data),
                }
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
        except Exception as e:
            logger.warning("S3 upload failed, fallback to local: %s", e)
        
        fallback = _upload_bytes_local(ip_id, file_name, content_type, data, force=True)
        if fallback:
            return fallback
        return None
    
    return _upload_bytes_local(ip_id, file_name, content_type, data, force=False)


def upload_stream(
    ip_id: str, 
    file_name: str, 
    content_type: str | None, 
    file_path: str,
    size_bytes: int
) -> dict[str, Any] | None:
    """
    流式上传文件（低内存上传）
    """
    cfg = get_storage_config()
    ext = Path(file_name or "").suffix
    file_id = f"file_{uuid.uuid4().hex[:20]}"
    object_key = f"ip/{ip_id}/{file_id}{ext}"
    
    # 计算 MD5
    try:
        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(64 * 1024), b''):
                md5_hash.update(chunk)
        content_md5 = base64.b64encode(md5_hash.digest()).decode('ascii')
    except Exception as e:
        logger.error("MD5 calculation failed: %s", e)
        return None
    
    # 优先 S3
    if cfg.get("s3_enabled"):
        try:
            client = _get_s3_client()
            bucket = cfg.get("bucket")
            if client and bucket:
                extra_args: dict[str, Any] = {"ContentMD5": content_md5}
                if content_type:
                    extra_args["ContentType"] = content_type
                
                with open(file_path, 'rb') as f:
                    client.put_object(Bucket=bucket, Key=object_key, Body=f, **extra_args)
                
                return {
                    "file_id": file_id,
                    "bucket": bucket,
                    "object_key": object_key,
                    "size_bytes": size_bytes,
                    "content_type": content_type,
                }
        except Exception as e:
            logger.warning("S3 stream upload failed: %s", e)
    
    # 本地存储回退
    return _upload_file_local(ip_id, file_name, content_type, file_path, size_bytes, object_key, file_id)


def _upload_file_local(
    ip_id: str,
    file_name: str,
    content_type: str | None,
    source_path: str,
    size_bytes: int,
    object_key: str,
    file_id: str,
) -> dict[str, Any] | None:
    """本地文件流式复制"""
    cfg = get_storage_config()
    if cfg.get("local_disabled"):
        logger.warning("Local storage disabled")
        return None
    
    try:
        base = Path(cfg["local_path"])
        full_path = base / object_key
        
        # 安全检查
        if not _is_safe_path(base, full_path):
            logger.warning("Path traversal blocked: %s", object_key)
            return None
        
        # 创建目录（使用 exist_ok 避免竞争条件）
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        shutil.copy2(source_path, full_path)
        
        return {
            "file_id": file_id,
            "bucket": LOCAL_BUCKET,
            "object_key": object_key,
            "size_bytes": size_bytes,
            "content_type": content_type,
        }
    except OSError as e:
        logger.error("Local file upload failed: %s", e)
        return None


def download_bytes(bucket: str, object_key: str) -> bytes | None:
    cfg = get_storage_config()
    
    if bucket == LOCAL_BUCKET:
        if cfg.get("local_disabled"):
            return None
        try:
            base = Path(cfg["local_path"])
            full_path = base / object_key
            
            if not _is_safe_path(base, full_path):
                logger.warning("Path traversal blocked in download: %s", object_key)
                return None
            
            if full_path.exists() and full_path.is_file():
                return full_path.read_bytes()
        except OSError as e:
            logger.error("Download failed: %s", e)
        return None
    
    client = _get_s3_client()
    if not client:
        return None
    try:
        resp = client.get_object(Bucket=bucket, Key=object_key)
        body = resp.get("Body")
        return body.read() if body else None
    except Exception as e:
        logger.error("S3 download failed: %s", e)
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
