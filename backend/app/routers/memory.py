import logging
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import FileObject, IngestTask, IPAsset
from app.services.ingest_service import get_ingest_task, process_ingest_task
from app.services.memory_config_service import get_ip
from app.services.storage_service import LOCAL_BUCKET, build_public_url, upload_bytes
from app.services.vector_service import query_similar_assets
from app.services.hybrid_retrieval_service import hybrid_search

router = APIRouter()
logger = logging.getLogger(__name__)


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


class UploadResponse(BaseModel):
    file_id: str
    file_url: str
    size_bytes: int
    content_type: Optional[str] = None


@router.post("/memory/ingest", response_model=IngestResponse)
def ingest_memory(
    payload: IngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Any:
    """
    素材录入：创建任务并加入后台队列，拉取内容后分块写入 ip_assets。
    source_url 与 local_file_id 至少填其一：文本/文档可走 URL 或本地上传；
    音视频可走 URL 或本地上传（需配置 Whisper / OPENAI_TRANSCRIPTION_*）。
    """
    if not get_ip(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    has_url = bool((payload.source_url or "").strip())
    has_file = bool((payload.local_file_id or "").strip())
    if not has_url and not has_file:
        raise HTTPException(
            status_code=400,
            detail="请提供 source_url，或先调用 POST /memory/upload 上传文件后传入 local_file_id",
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

    # 使用线程后台执行，避免长时间阻塞
    import threading
    thread = threading.Thread(target=process_ingest_task, args=(task_id,))
    thread.daemon = True
    thread.start()
    
    return IngestResponse(ingest_task_id=task_id, status="QUEUED")


@router.post("/memory/upload", response_model=UploadResponse)
async def upload_memory_file(
    ip_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Any:
    """
    上传文件到对象存储，返回 local_file_id（file_id）。
    可配合 /memory/ingest 的 local_file_id 使用。
    """
    if not get_ip(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="文件过大，当前上限 100MB")

    result = upload_bytes(ip_id, file.filename or "upload.bin", file.content_type, data)
    if not result:
        raise HTTPException(
            status_code=503,
            detail="存储不可用：请检查 STORAGE_* 凭证与网络，或关闭 STORAGE_LOCAL_DISABLED 并确保本地目录可写；详见服务端日志。",
        )

    row = FileObject(
        file_id=result["file_id"],
        ip_id=ip_id,
        provider="local" if result.get("bucket") == LOCAL_BUCKET else "s3",
        bucket=result["bucket"],
        object_key=result["object_key"],
        file_name=file.filename,
        content_type=file.content_type,
        size_bytes=result["size_bytes"],
    )
    try:
        db.add(row)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("memory upload: failed to persist file_objects row")
        raise HTTPException(
            status_code=503,
            detail="写入数据库失败，请确认已执行迁移（含 file_objects 表）且与当前数据库一致。",
        ) from e

    file_url = build_public_url(result["bucket"], result["object_key"])
    return UploadResponse(
        file_id=row.file_id,
        file_url=file_url,
        size_bytes=row.size_bytes,
        content_type=row.content_type,
    )


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
    raw_ids = task.created_asset_ids
    if raw_ids is None:
        created_assets: List[str] = []
    elif isinstance(raw_ids, list):
        created_assets = [str(x) for x in raw_ids]
    else:
        created_assets = []
    return IngestStatusResponse(
        ingest_task_id=task.task_id,
        status=task.status,
        error=task.error_message,
        created_assets=created_assets,
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

    # 优先向量检索；不可用时回退关键词检索
    vec_hits = query_similar_assets(db, ip_id=payload.ip_id, query=query, top_k=top_k)
    if vec_hits:
        hit_ids = [h["asset_id"] for h in vec_hits]
        sim_map = {h["asset_id"]: h["similarity"] for h in vec_hits}
        rows = db.query(IPAsset).filter(IPAsset.asset_id.in_(hit_ids)).all()
        row_map = {r.asset_id: r for r in rows}
        results: list[RetrieveResultItem] = []
        for aid in hit_ids:
            r = row_map.get(aid)
            if not r:
                continue
            snippet = (r.content or "")[:220] + ("..." if len(r.content or "") > 220 else "")
            results.append(
                RetrieveResultItem(
                    asset_id=r.asset_id,
                    title=r.title,
                    content_snippet=snippet,
                    metadata=r.asset_meta or {},
                    similarity=float(sim_map.get(aid, 0.0)),
                )
            )
        return RetrieveResponse(results=results)

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


class HybridRetrieveRequest(BaseModel):
    ip_id: str
    query: str
    top_k: Optional[int] = 10
    vector_weight: Optional[float] = Field(0.6, description="向量检索权重")
    graph_weight: Optional[float] = Field(0.4, description="Graph RAG权重")
    use_vector: Optional[bool] = True
    use_graph: Optional[bool] = True


class HybridRetrieveResponse(BaseModel):
    query: str
    ip_id: str
    total: int
    results: list
    config: dict


@router.post("/memory/retrieve/hybrid", response_model=HybridRetrieveResponse)
def retrieve_hybrid(
    payload: HybridRetrieveRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    混合检索 - 向量 + Graph RAG 融合检索
    
    结合向量语义理解和知识图谱关系推理，提供更精准的检索结果。
    支持动态调整向量/图谱权重。
    """
    if not get_ip(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    
    query = (payload.query or "").strip()
    if not query:
        return HybridRetrieveResponse(
            query="",
            ip_id=payload.ip_id,
            total=0,
            results=[],
            config={},
        )
    
    result = hybrid_search(
        db=db,
        ip_id=payload.ip_id,
        query=query,
        vector_weight=payload.vector_weight,
        graph_weight=payload.graph_weight,
        top_k=payload.top_k or 10,
        use_vector=payload.use_vector,
        use_graph=payload.use_graph,
    )
    
    return HybridRetrieveResponse(**result)


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
