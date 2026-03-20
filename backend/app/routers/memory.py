import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IngestTask, IPAsset
from app.services.ingest_service import get_ingest_task, process_ingest_task
from app.services.memory_config_service import get_ip

router = APIRouter()


class AssetItem(BaseModel):
    asset_id: str
    title: Optional[str] = None
    content_snippet: Optional[str] = None
    asset_type: str
    metadata: dict = Field(default_factory=dict)


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


@router.get("/memory/assets")
def list_assets(
    ip_id: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> Any:
    """
    列出指定 IP 的素材（ip_assets），用于业务实测时验证录入/同步结果。
    """
    if not get_ip(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    rows = (
        db.query(IPAsset)
        .filter(IPAsset.ip_id == ip_id, IPAsset.status == "active")
        .order_by(IPAsset.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = []
    for r in rows:
        snippet = (r.content or "")[:200] + ("..." if len(r.content or "") > 200 else "")
        items.append(
            AssetItem(
                asset_id=r.asset_id,
                title=r.title,
                content_snippet=snippet,
                asset_type=r.asset_type,
                metadata=r.asset_meta or {},
            )
        )
    total = db.query(IPAsset).filter(IPAsset.ip_id == ip_id, IPAsset.status == "active").count()
    return {"items": items, "total": total}


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
def retrieve_memory(payload: RetrieveRequest, db: Session = Depends(get_db)) -> Any:
    """
    语义检索接口。未接入向量库前使用简易关键词匹配（content ILIKE），便于业务实测。
    """
    if not get_ip(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    query = (payload.query or "").strip()
    top_k = min(payload.top_k or 10, 50)
    if not query:
        return RetrieveResponse(results=[])

    esc = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{esc}%"

    q = (
        db.query(IPAsset)
        .filter(
            IPAsset.ip_id == payload.ip_id,
            IPAsset.status == "active",
            IPAsset.content.isnot(None),
            IPAsset.content.ilike(pattern, escape="\\"),
        )
        .order_by(IPAsset.updated_at.desc())
        .limit(top_k)
    )
    rows = q.all()
    results = []
    for r in rows:
        idx = (r.content or "").lower().find(query.lower())
        start = max(0, idx - 50)
        end = min(len(r.content or ""), idx + len(query) + 80)
        snippet = (r.content or "")[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(r.content or ""):
            snippet = snippet + "..."
        results.append(
            RetrieveResultItem(
                asset_id=r.asset_id,
                title=r.title,
                content_snippet=snippet or r.content[:200] if r.content else None,
                metadata=r.asset_meta or {},
                similarity=0.9,
            )
        )
    return RetrieveResponse(results=results)


@router.get("/memory/pending-labels", response_model=PendingLabelsResponse)
def list_pending_labels(
    ip_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> Any:
    """
    自动打标待复核列表。返回尚未确认标签的素材（metadata 无 confirmed_labels），
    便于业务实测。
    """
    if not get_ip(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")

    rows = (
        db.query(IPAsset)
        .filter(IPAsset.ip_id == ip_id, IPAsset.status == "active")
        .order_by(IPAsset.updated_at.desc())
        .limit(limit * 2)
        .all()
    )
    pending = [r for r in rows if not (r.asset_meta or {}).get("confirmed_labels")][:limit]
    items = []
    for r in pending:
        meta = r.asset_meta or {}
        auto_labels = meta.get("auto_labels")
        if auto_labels is None:
            auto_labels = meta.get("source_type", meta) or {}
        if isinstance(auto_labels, str):
            auto_labels = {"source": auto_labels}
        if not isinstance(auto_labels, dict):
            auto_labels = {}
        items.append(
            PendingLabelsItem(
                asset_id=r.asset_id,
                title=r.title,
                source=meta.get("source", "ingest"),
                content_snippet=(r.content or "")[:300] + ("..." if len(r.content or "") > 300 else ""),
                auto_labels=auto_labels,
            )
        )
    return PendingLabelsResponse(items=items)


@router.post("/memory/labels/{asset_id}")
def update_labels(
    asset_id: str,
    payload: UpdateLabelsRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    确认素材标签，写入 asset metadata 的 confirmed_labels，便于业务实测。
    """
    if not get_ip(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    row = db.query(IPAsset).filter(IPAsset.asset_id == asset_id, IPAsset.ip_id == payload.ip_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"素材不存在: {asset_id}")

    meta = dict(row.asset_meta or {})
    meta["confirmed_labels"] = payload.confirmed_labels
    row.asset_meta = meta
    db.commit()
    return {"success": True}
