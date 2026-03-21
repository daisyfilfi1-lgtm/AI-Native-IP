"""
向量存储与检索（Phase 1）。
当前使用 PostgreSQL JSONB 存储向量，后续可平滑迁移到 pgvector 或外部向量库。
"""
from math import sqrt
from typing import Any

from sqlalchemy.orm import Session

from app.config.ai_config import get_ai_config
from app.db.models import AssetVector
from app.services.ai_client import embed


def upsert_asset_vector(
    db: Session,
    *,
    asset_id: str,
    ip_id: str,
    content: str,
    precomputed_embedding: list[float] | None = None,
) -> bool:
    """
    写入 asset_vectors。若已在外部批量算好向量，传入 precomputed_embedding 可避免重复调用 Embedding API。
    """
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


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a))
    nb = sqrt(sum(y * y for y in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


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

    rows = (
        db.query(AssetVector)
        .filter(AssetVector.ip_id == ip_id)
        .all()
    )
    scored: list[tuple[str, float]] = []
    for r in rows:
        vec = r.embedding if isinstance(r.embedding, list) else []
        sim = _cosine_similarity(query_vec, vec)
        if sim > 0:
            scored.append((r.asset_id, sim))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [{"asset_id": aid, "similarity": sim} for aid, sim in scored[:top_k]]
