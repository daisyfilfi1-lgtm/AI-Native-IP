import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IngestTask
from app.services.ingest_service import get_ingest_task, process_ingest_task
from app.services.memory_config_service import get_ip

router = APIRouter()


class IngestRequest(BaseModel):
    ip_id: str
    source_type: str = Field(..., description="video|audio|text|document")
    source_url: Optional[str] = None
    local_file_id: Optional[str] = None
    title: Optional[str] = None
    notes: Optional[str] = None


class IngestResponse(BaseModel):
    ingest_task_id: str
    status: str


class IngestStatusResponse(BaseModel):
    ingest_task_id: str
    status: str
    error: Optional[str] = None
    created_assets: List[str] = Field(default_factory=list)


class RetrieveFilters(BaseModel):
    emotion_tags: Optional[List[str]] = None
    scene_tags: Optional[List[str]] = None
    max_usage_ratio: Optional[float] = None


class RetrieveRequest(BaseModel):
    ip_id: str
    query: str
    filters: Optional[RetrieveFilters] = None
    top_k: Optional[int] = None


class RetrieveResultItem(BaseModel):
    asset_id: str
    title: Optional[str] = None
    content_snippet: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    similarity: float


class RetrieveResponse(BaseModel):
    results: List[RetrieveResultItem]


class PendingLabelsItem(BaseModel):
    asset_id: str
    title: Optional[str] = None
    source: Optional[str] = None
    content_snippet: Optional[str] = None
    auto_labels: dict


class PendingLabelsResponse(BaseModel):
    items: List[PendingLabelsItem]


class UpdateLabelsRequest(BaseModel):
    ip_id: str
    confirmed_labels: dict


@router.post("/memory/ingest", response_model=IngestResponse)
def ingest_memory(
    payload: IngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Any:
    """
    素材录入：创建任务并加入后台队列，拉取内容后分块写入 ip_assets。
    需提供 source_url（text/document）或 local_file_id；video/audio 暂为占位。
    """
    if not get_ip(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    if payload.source_type in ("text", "document") and not payload.source_url:
        raise HTTPException(
            status_code=400,
            detail="text/document 类型需提供 source_url",
        )

    task_id = f"ingest_{uuid.uuid4().hex[:16]}"
    task = IngestTask(
        task_id=task_id,
        ip_id=payload.ip_id,
        source_type=payload.source_type,
        source_url=payload.source_url,
        local_file_id=payload.local_file_id,
        title=payload.title,
        notes=payload.notes,
        status="QUEUED",
        created_asset_ids=[],
    )
    db.add(task)
    db.commit()

    background_tasks.add_task(process_ingest_task, task_id)
    return IngestResponse(ingest_task_id=task_id, status="QUEUED")


@router.get("/memory/ingest/{task_id}", response_model=IngestStatusResponse)
def get_ingest_status(task_id: str, db: Session = Depends(get_db)) -> Any:
    """查询素材录入任务状态及产生的 asset 列表。"""
    task = get_ingest_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return IngestStatusResponse(
        ingest_task_id=task.task_id,
        status=task.status,
        error=task.error_message,
        created_assets=task.created_asset_ids or [],
    )


@router.post("/memory/retrieve", response_model=RetrieveResponse)
def retrieve_memory(payload: RetrieveRequest) -> Any:
    """
    语义检索接口（Phase 1 占位实现）
    目前返回空结果，后续接入向量库与检索逻辑。
    """
    return RetrieveResponse(results=[])


@router.get("/memory/pending-labels", response_model=PendingLabelsResponse)
def list_pending_labels(ip_id: str, limit: int = 20) -> Any:
    """
    自动打标待复核列表（Phase 1 占位实现）
    """
    return PendingLabelsResponse(items=[])


@router.post("/memory/labels/{asset_id}")
def update_labels(asset_id: str, payload: UpdateLabelsRequest) -> Any:
    """
    更新素材标签（Phase 1 占位实现）
    """
    return {"success": True}
