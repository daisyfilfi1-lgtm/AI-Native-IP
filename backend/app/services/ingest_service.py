"""
素材录入流水线：根据任务拉取内容、分块、写入 ip_assets，并更新 ingest_tasks。
支持：text/document 的 URL 或本地上传（UTF-8 文本）；video/audio 的 URL 或本地上传（Whisper 转写）。
已配置 LLM 时，会自动调用打标（asset_meta.auto_labels）。
"""
import os
import tempfile
import uuid
from pathlib import Path
from typing import List

import requests
from sqlalchemy.orm import Session

from app.db.models import FileObject, IPAsset, IngestTask, TagConfig
from app.services.ai_client import suggest_tags_for_content, transcribe, transcribe_from_url
from app.db.session import SessionLocal
from app.services.storage_service import download_bytes
from app.services.vector_service import upsert_asset_vector

# 分块默认长度（字符），可按需调整
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 100


def get_ingest_task(db: Session, task_id: str) -> IngestTask | None:
    return db.query(IngestTask).filter(IngestTask.task_id == task_id).first()


def _fetch_text_from_url(url: str) -> str:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.encoding or "utf-8"
    return resp.text


def _transcribe_from_file_object(db: Session, task: IngestTask) -> str:
    """从对象存储已上传文件转写音视频（Whisper）。"""
    if not task.local_file_id:
        return ""
    row = (
        db.query(FileObject)
        .filter(FileObject.file_id == task.local_file_id, FileObject.ip_id == task.ip_id)
        .first()
    )
    if not row:
        return ""
    data = download_bytes(row.bucket, row.object_key)
    if not data:
        return ""
    suffix = Path(row.file_name or row.object_key or "").suffix or ".bin"
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        return (transcribe(tmp_path) or "").strip()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _load_text_from_file_object(db: Session, task: IngestTask) -> str:
    if not task.local_file_id:
        return ""
    row = (
        db.query(FileObject)
        .filter(FileObject.file_id == task.local_file_id, FileObject.ip_id == task.ip_id)
        .first()
    )
    if not row:
        return ""
    data = download_bytes(row.bucket, row.object_key)
    if not data:
        return ""
    # Phase 1: 文本类文件按 utf-8 读取；复杂格式后续接文档解析服务
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """按长度分块，带重叠，避免截断在句中对齐到换行。"""
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # 尽量在换行处截断
            last_nl = text.rfind("\n", start, end + 1)
            if last_nl > start:
                end = last_nl + 1
        chunks.append(text[start:end].strip())
        if not chunks[-1]:
            start = end
            continue
        start = end - overlap
        if start >= len(text):
            break
    return [c for c in chunks if c]


def _run_ingest_pipeline(db: Session, task: IngestTask) -> None:
    """执行录入：拉取内容 → 分块 → 写入 ip_assets → 更新 task。"""
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Starting pipeline for task: %s", task.task_id)

    task.status = "PROCESSING"
    db.commit()

    try:
        st = task.source_type or "text"
        if st in ("video", "audio") and task.local_file_id:
            raw_text = _transcribe_from_file_object(db, task)
            if not (raw_text or "").strip():
                raw_text = (
                    f"[{st} 转写失败或未配置 Whisper] {task.title or task.local_file_id}\n\n"
                    "请检查 OPENAI_TRANSCRIPTION_API_KEY（或主 OPENAI_API_KEY）及文件格式。"
                )
        elif st in ("video", "audio") and task.source_url:
            raw_text = transcribe_from_url(task.source_url)
            if not (raw_text or "").strip():
                raw_text = (
                    f"[{st} 转写失败或未配置 Whisper] {task.title or task.source_url or '未命名'}\n\n"
                    "请检查转写 API 及网络。"
                )
        elif st in ("text", "document", "file") and task.local_file_id:
            raw_text = _load_text_from_file_object(db, task)
            if not raw_text.strip():
                raw_text = (
                    f"[文件解析失败] {task.title or task.local_file_id}\n\n"
                    "当前仅内置 utf-8 文本解析，复杂文档建议走文档解析服务。"
                )
        elif st in ("text", "document", "file") and task.source_url:
            raw_text = _fetch_text_from_url(task.source_url)
        elif task.local_file_id:
            raw_text = _load_text_from_file_object(db, task)
            if not (raw_text or "").strip():
                raw_text = _transcribe_from_file_object(db, task)
            if not (raw_text or "").strip():
                raw_text = (
                    f"[文件解析失败] {task.title or task.local_file_id}\n\n"
                    "请确认 source_type 为 text/document/file（文本）或 audio/video（音视频）。"
                )
        elif st in ("video", "audio"):
            raw_text = (
                f"[{st} 待转写] {task.title or '未命名'}\n\n"
                "请填写 source_url，或先上传文件并传入 local_file_id。"
            )
        else:
            raw_text = f"[待处理] {task.title or '未命名'}\n\nsource_type={st}"

        chunks = _chunk_text(raw_text)
        if not chunks:
            chunks = [raw_text or "(无内容)"]

        tag_cfg = db.query(TagConfig).filter(TagConfig.ip_id == task.ip_id).first()
        categories = (tag_cfg.tag_categories if tag_cfg else None) or None

        created_ids: List[str] = []
        for i, content in enumerate(chunks):
            asset_id = f"asset_{task.ip_id}_{uuid.uuid4().hex[:12]}"
            title = (task.title or "未命名") + (f" (片段{i+1})" if len(chunks) > 1 else "")
            meta: dict = {
                "source_task_id": task.task_id,
                "source_type": task.source_type,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            # TODO: Re-enable with proper async handling, timeouts, and resource
            # limits. Disabled because LLM API calls can hang indefinitely and
            # cause the service to be OOM-killed before the task completes.
            # try:
            #     tags = suggest_tags_for_content(content, categories)
            #     if tags:
            #         meta["auto_labels"] = tags
            # except Exception:
            #     pass
            db.add(
                IPAsset(
                    asset_id=asset_id,
                    ip_id=task.ip_id,
                    asset_type="story",
                    title=title,
                    content=content,
                    content_vector_ref=None,
                    asset_meta=meta,
                    relations=[],
                    status="active",
                )
            )
            # TODO: Re-enable with proper async handling, timeouts, and resource
            # limits. Disabled because vector embedding operations are slow and
            # memory-intensive, causing OOM kills during background task execution.
            # try:
            #     upsert_asset_vector(
            #         db,
            #         asset_id=asset_id,
            #         ip_id=task.ip_id,
            #         content=content,
            #     )
            # except Exception:
            #     pass
            created_ids.append(asset_id)

        task.status = "COMPLETED"
        task.created_asset_ids = created_ids
        task.error_message = None
    except Exception as e:
        logger.exception("ingest pipeline failed: %s", task.task_id)
        task.status = "FAILED"
        task.error_message = str(e)
        task.created_asset_ids = []

    db.commit()


def process_ingest_task(task_id: str) -> None:
    """
    后台执行录入任务（在独立会话中）。
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Starting ingest task: {task_id}")
    
    db = SessionLocal()
    try:
        task = get_ingest_task(db, task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return
        if task.status != "QUEUED":
            logger.warning(f"Task {task_id} status is {task.status}, expected QUEUED")
            return
            
        logger.info(f"Running pipeline for task: {task_id}")
        _run_ingest_pipeline(db, task)
        logger.info(f"Completed task: {task_id}")
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {e}")
        task = get_ingest_task(db, task_id)
        if task:
            task.status = "FAILED"
            task.error_message = str(e)
            db.commit()
    finally:
        db.close()
