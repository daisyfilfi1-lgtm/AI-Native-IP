"""
素材录入流水线：根据任务拉取内容、分块、写入 ip_assets，并更新 ingest_tasks。
Phase 1 支持 text/document 类型的 source_url 拉取；video/audio 占位（可后续接 Whisper）。
"""
import uuid
from typing import List

import requests
from sqlalchemy.orm import Session

from app.db.models import IPAsset, IngestTask
from app.db.session import SessionLocal

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
    task.status = "PROCESSING"
    db.commit()

    try:
        if task.source_type in ("text", "document") and task.source_url:
            raw_text = _fetch_text_from_url(task.source_url)
        elif task.source_type in ("video", "audio"):
            # Phase 1 占位：暂无 Whisper，写入一条占位素材便于流程跑通
            raw_text = f"[{task.source_type} 待转写] {task.title or task.source_url or '未命名'}\n\n后续接入 ASR 后可在此写入转写文本。"
        else:
            # 仅 local_file_id 等暂不支持时，写入一条占位
            raw_text = f"[待处理] {task.title or '未命名'}\n\nsource_type={task.source_type}"

        chunks = _chunk_text(raw_text)
        if not chunks:
            chunks = [raw_text or "(无内容)"]

        created_ids: List[str] = []
        for i, content in enumerate(chunks):
            asset_id = f"asset_{task.ip_id}_{uuid.uuid4().hex[:12]}"
            title = (task.title or "未命名") + (f" (片段{i+1})" if len(chunks) > 1 else "")
            db.add(
                IPAsset(
                    asset_id=asset_id,
                    ip_id=task.ip_id,
                    asset_type="story",
                    title=title,
                    content=content,
                    content_vector_ref=None,
                    asset_meta={
                        "source_task_id": task.task_id,
                        "source_type": task.source_type,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    },
                    relations=[],
                    status="active",
                )
            )
            created_ids.append(asset_id)

        task.status = "COMPLETED"
        task.created_asset_ids = created_ids
        task.error_message = None
    except Exception as e:
        task.status = "FAILED"
        task.error_message = str(e)
        task.created_asset_ids = []

    db.commit()


def process_ingest_task(task_id: str) -> None:
    """
    后台执行录入任务（在独立会话中）。
    由路由在 BackgroundTasks 中调用，或由 Celery 等队列调用。
    """
    db = SessionLocal()
    try:
        task = get_ingest_task(db, task_id)
        if not task:
            return
        if task.status != "QUEUED":
            return
        _run_ingest_pipeline(db, task)
    finally:
        db.close()
