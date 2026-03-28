"""
向量存储与检索。使用 pgvector 原生向量类型，支持高效相似度检索。
"""
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.ai_config import get_ai_config
from app.db.models import AssetVector
from app.services.ai_client import embed


def _normalize_embedding_dim(vec: list[float], target_dim: int = 1536) -> list[float]:
    """将任意维度 embedding 归一到 pgvector 列维度。"""
    if not vec:
        return []
    if len(vec) == target_dim:
        return vec
    if len(vec) > target_dim:
        return vec[:target_dim]
    # 短向量右侧补零，保持语义方向并兼容固定维度存储
    return vec + [0.0] * (target_dim - len(vec))


def upsert_asset_vector(
    db: Session,
    *,
    asset_id: str,
    ip_id: str,
    content: str,
    precomputed_embedding: list[float] | None = None,
    force: bool = False,
) -> bool:
    """
    写入 asset_vectors。若已在外部批量算好向量，传入 precomputed_embedding 可避免重复调用 Embedding API。
    """
    if (not force) and os.environ.get("INGEST_SKIP_EMBEDDING", "").lower() in ("1", "true", "yes"):
        return False
    text = (content or "").strip()
    if precomputed_embedding is not None:
        vec = precomputed_embedding
    else:
        if not text:
            return False
        vectors = embed([text])
        if not vectors or not vectors[0]:
            return False
        vec = vectors[0]
    vec = _normalize_embedding_dim(vec, 1536)
    if len(vec) != 1536:
        return False
    cfg = get_ai_config()
    model = cfg.get("embedding_model") or "text-embedding-3-small"
    row = db.query(AssetVector).filter(AssetVector.asset_id == asset_id).first()
    if row:
        row.embedding = vec
        row.dim = len(vec)
        row.model = model
    else:
        db.add(
            AssetVector(
                asset_id=asset_id,
                ip_id=ip_id,
                embedding=vec,
                dim=len(vec),
                model=model,
            )
        )
    return True


def query_similar_assets(
    db: Session,
    *,
    ip_id: str,
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    qv = embed([q])
    if not qv or not qv[0]:
        return []
    query_vec = qv[0]
    query_vec = _normalize_embedding_dim(query_vec, 1536)
    if len(query_vec) != 1536:
        return []

    dist = AssetVector.embedding.cosine_distance(query_vec)
    stmt = (
        select(AssetVector.asset_id, dist.label("d"))
        .where(AssetVector.ip_id == ip_id)
        .order_by(dist.asc())
        .limit(max(1, top_k))
    )
    rows = db.execute(stmt).all()
    return [
        {"asset_id": aid, "similarity": max(0, 1.0 - d)}
        for aid, d in rows
    ]
