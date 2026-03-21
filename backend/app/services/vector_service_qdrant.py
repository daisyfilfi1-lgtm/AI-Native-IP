"""
向量存储与检索 - Qdrant实现
Phase 2: 从PostgreSQL JSONB迁移到专用向量库Qdrant
"""
import os
from typing import Any, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.http.models import (
    Distance,
    Filter,
    MatchText,
    PointStruct,
    SearchParams,
    TextIndexParams,
    TokenizerType,
)
from sqlalchemy.orm import Session

from app.config.ai_config import get_ai_config
from app.db.models import AssetVector
from app.services.ai_client import embed


# Qdrant配置
def get_qdrant_client() -> QdrantClient:
    """获取Qdrant客户端，支持本地或云端。未连接时调用方会降级到 PostgreSQL。"""
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.environ.get("QDRANT_API_KEY", "").strip() or None
    return QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
        timeout=30,
        check_compatibility=False,  # 避免版本检查导致的 403/连接失败
    )


def get_collection_name(ip_id: str) -> str:
    """获取IP对应的collection名称"""
    return f"ip_{ip_id}"


def ensure_collection(client: QdrantClient, ip_id: str, vector_size: int = 1536) -> None:
    """
    确保IP对应的collection存在，不存在则创建
    使用DeepSeek embedding (1536维)
    """
    collection_name = get_collection_name(ip_id)
    
    try:
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
    except ResponseHandlingException:
        exists = False
    
    if not exists:
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "text": {
                    "size": vector_size,
                    "distance": Distance.COSINE,
                }
            },
            # 启用药材文本索引支持混合搜索
            sparse_vectors_config={
                "text": {
                    "index": TextIndexParams(
                        tokenizer=TokenizerType.PORTER,
                        min_token_len=2,
                        max_token_len=15,
                        mode=TextIndexParams.Mode.NORMAL,
                    )
                }
            },
        )


def upsert_asset_vector(
    db: Session,
    *,
    asset_id: str,
    ip_id: str,
    content: str,
    metadata: Optional[dict] = None,
) -> bool:
    """
    将素材向量写入Qdrant
    同时保持PostgreSQL的AssetVector表同步（向后兼容）
    """
    text = (content or "").strip()
    if not text:
        return False
    
    # 生成embedding
    vectors = embed([text])
    if not vectors or not vectors[0]:
        return False
    vec = vectors[0]
    
    cfg = get_ai_config()
    model = cfg.get("embedding_model") or "deepseek-embedding"
    
    # 写入Qdrant
    try:
        client = get_qdrant_client()
        ensure_collection(client, ip_id, len(vec))
        
        point = PointStruct(
            id=asset_id,
            vector={
                "text": vec,
            },
            payload={
                "asset_id": asset_id,
                "ip_id": ip_id,
                "content": text[:5000],  # Qdrant限制payload大小，截断
                "metadata": metadata or {},
            },
        )
        
        client.upsert(
            collection_name=get_collection_name(ip_id),
            points=[point],
        )
    except Exception as e:
        print(f"Qdrant upsert failed: {e}")
        # Qdrant失败时降级到PostgreSQL
        pass
    
    # 保持PostgreSQL向后兼容（可选：后续可移除）
    try:
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
        db.commit()
    except Exception:
        db.rollback()
    
    return True


def delete_asset_vector(
    db: Session,
    *,
    asset_id: str,
    ip_id: str,
) -> bool:
    """从Qdrant删除向量"""
    try:
        client = get_qdrant_client()
        client.delete(
            collection_name=get_collection_name(ip_id),
            points_selector=[asset_id],
        )
    except Exception as e:
        print(f"Qdrant delete failed: {e}")
    
    # 同步删除PostgreSQL记录
    try:
        row = db.query(AssetVector).filter(AssetVector.asset_id == asset_id).first()
        if row:
            db.delete(row)
            db.commit()
    except Exception:
        db.rollback()
    
    return True


def query_similar_assets(
    db: Session,
    *,
    ip_id: str,
    query: str,
    top_k: int,
    filter_conditions: Optional[dict] = None,
    use_hybrid: bool = True,
) -> list[dict[str, Any]]:
    """
    向量检索 - Qdrant实现
    
    支持两种模式：
    - 向量相似度搜索 (use_hybrid=False)
    - 混合搜索：向量 + 关键词 (use_hybrid=True) - 更精准
    """
    q = (query or "").strip()
    if not q:
        return []
    
    # 生成query向量
    qv = embed([q])
    if not qv or not qv[0]:
        return []
    query_vec = qv[0]
    
    try:
        client = get_qdrant_client()
        collection_name = get_collection_name(ip_id)
        
        # 构建过滤条件
        qdrant_filter = None
        if filter_conditions:
            must_conditions = []
            for key, value in filter_conditions.items():
                if isinstance(value, list):
                    must_conditions.append(
                        Filter(must=[MatchText(key=key, text=v) for v in value])
                    )
                else:
                    must_conditions.append(
                        Filter(must=[MatchText(key=key, text=value)])
                    )
            if must_conditions:
                qdrant_filter = Filter(must=must_conditions)
        
        search_params = SearchParams(
            hnsw_ef=128,  # 加速检索
            exact=False,
        )
        
        if use_hybrid:
            # 混合搜索：融合向量和关键词
            results = client.search(
                collection_name=collection_name,
                query_vector=("text", query_vec),
                query_text=q,  # 关键词补充
                limit=top_k,
                search_params=search_params,
                with_payload=True,
                with_vectors=False,
            )
        else:
            # 纯向量搜索
            results = client.search(
                collection_name=collection_name,
                query_vector=("text", query_vec),
                limit=top_k,
                search_params=search_params,
                with_payload=True,
                with_vectors=False,
            )
        
        return [
            {
                "asset_id": r.id,
                "similarity": r.score,
                "content": r.payload.get("content", ""),
                "metadata": r.payload.get("metadata", {}),
            }
            for r in results
        ]
        
    except Exception as e:
        print(f"Qdrant search failed, falling back to PostgreSQL: {e}")
        # 降级到PostgreSQL
        return _fallback_postgres_search(db, ip_id, query_vec, top_k)


def _fallback_postgres_search(
    db: Session,
    ip_id: str,
    query_vec: list[float],
    top_k: int,
) -> list[dict[str, Any]]:
    """PostgreSQL回退搜索（使用余弦相似度）"""
    from math import sqrt
    
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sqrt(sum(x * x for x in a))
        nb = sqrt(sum(y * y for y in b))
        if na <= 0 or nb <= 0:
            return 0.0
        return dot / (na * nb)
    
    rows = db.query(AssetVector).filter(AssetVector.ip_id == ip_id).all()
    scored = []
    for r in rows:
        vec = r.embedding if isinstance(r.embedding, list) else []
        sim = cosine_similarity(query_vec, vec)
        if sim > 0:
            scored.append((r.asset_id, sim))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # 获取完整asset信息
    hit_ids = [aid for aid, _ in scored[:top_k]]
    assets = db.query(AssetVector).filter(AssetVector.asset_id.in_(hit_ids)).all()
    asset_map = {a.asset_id: a for a in assets}
    
    results = []
    for aid, sim in scored[:top_k]:
        r = asset_map.get(aid)
        if r:
            results.append({
                "asset_id": aid,
                "similarity": sim,
                "content": "",
                "metadata": {},
            })
    return results


def get_collection_info(ip_id: str) -> dict:
    """获取IP的向量Collection信息"""
    try:
        client = get_qdrant_client()
        info = client.get_collection(collection_name=get_collection_name(ip_id))
        return {
            "name": info.name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.name,
        }
    except Exception as e:
        return {"error": str(e)}


def delete_collection(ip_id: str) -> bool:
    """删除IP的整个向量Collection"""
    try:
        client = get_qdrant_client()
        client.delete_collection(collection_name=get_collection_name(ip_id))
        return True
    except Exception as e:
        print(f"Delete collection failed: {e}")
        return False
