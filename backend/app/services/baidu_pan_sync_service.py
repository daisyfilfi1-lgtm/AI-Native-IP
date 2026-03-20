"""
百度网盘目录 → Memory（ip_assets）同步：拉取文本类文件写入/更新 ip_assets。
"""
from __future__ import annotations

import hashlib
from collections import deque
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.baidu_pan_client import (
    download_file_bytes,
    is_dir,
    list_dir,
)
from app.services.vector_service import upsert_asset_vector

# 同步的文本类后缀；单文件大小上限（字节）
TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".csv", ".log", ".yaml", ".yml"}
MAX_BYTES = 10 * 1024 * 1024


def _iter_files_recursive(
    access_token: str,
    root_path: str,
    *,
    max_files: int = 200,
) -> list[dict[str, Any]]:
    """BFS 遍历目录，收集文件项（含 path）。"""
    root = root_path.rstrip("/") or "/"
    queue: deque[str] = deque([root if root.startswith("/") else "/" + root])
    seen: set[str] = set()
    files: list[dict[str, Any]] = []
    while queue and len(files) < max_files:
        cur = queue.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        try:
            items = list_dir(access_token, cur)
        except Exception:
            continue
        for item in items:
            if len(files) >= max_files:
                break
            path = item.get("path") or ""
            if not path:
                continue
            if is_dir(item):
                if path not in seen:
                    queue.append(path)
                continue
            files.append(item)
    return files


def sync_baidu_netdisk_to_ip(
    db: Session,
    ip_id: str,
    access_token: str,
    remote_path: str = "/",
    *,
    recursive: bool = True,
) -> dict[str, Any]:
    """
    将百度网盘指定目录下的文本文件同步到 ip_assets。
    - remote_path: 网盘目录，如 '/' 或 '/我的资源/笔记'
    - recursive: 是否递归子目录（有 max_files 上限）
    """
    synced = 0
    failed = 0
    errors: list[str] = []

    rp = (remote_path or "/").strip()
    if not rp.startswith("/"):
        rp = "/" + rp

    try:
        if recursive:
            candidates = _iter_files_recursive(access_token, rp)
        else:
            candidates = [x for x in list_dir(access_token, rp) if not is_dir(x)]
    except Exception as e:
        return {"synced": 0, "failed": 0, "errors": [f"列目录失败: {e}"]}

    for item in candidates:
        path = item.get("path") or ""
        name = (item.get("server_filename") or Path(path).name or "").strip()
        if not path:
            continue
        ext = Path(name).suffix.lower()
        if ext not in TEXT_EXTENSIONS:
            continue
        size = int(item.get("size") or 0)
        if size > MAX_BYTES:
            errors.append(f"{name}: 文件过大(>{MAX_BYTES // (1024*1024)}MB)，已跳过")
            continue
        try:
            content_bytes = download_file_bytes(access_token, path)
        except Exception as e:
            failed += 1
            errors.append(f"{name}: {e}")
            continue
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = content_bytes.decode("utf-8", errors="ignore")

        raw = f"baidu_{path}"
        asset_id = "baidu_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
        title = name or "未命名"
        meta = {
            "source": "baidu_netdisk",
            "baidu_path": path,
        }

        existing = db.query(IPAsset).filter(IPAsset.asset_id == asset_id).first()
        if existing:
            existing.title = title
            existing.content = content if content else "(无文本)"
            base_meta = existing.asset_meta if existing.asset_meta else {}
            existing.asset_meta = {**base_meta, **meta}
            db.flush()
            try:
                upsert_asset_vector(db, asset_id=existing.asset_id, ip_id=ip_id, content=existing.content or "")
            except Exception:
                pass
        else:
            db.add(
                IPAsset(
                    asset_id=asset_id,
                    ip_id=ip_id,
                    asset_type="data",
                    title=title,
                    content=content or "(无文本)",
                    content_vector_ref=None,
                    asset_meta=meta,
                    relations=[],
                    status="active",
                )
            )
            db.flush()
            try:
                upsert_asset_vector(db, asset_id=asset_id, ip_id=ip_id, content=content or "")
            except Exception:
                pass
        synced += 1

    db.commit()
    return {"synced": synced, "failed": failed, "errors": errors[:30]}
