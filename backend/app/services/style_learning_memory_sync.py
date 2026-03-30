"""
将「文案学习要点」同步到 Memory 向量库（IPAsset + Qdrant + pgvector AssetVector），
供 hybrid 检索、pgvector 风格检索与后续 RAG 使用。
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.vector_service_qdrant import upsert_asset_vector as qdrant_upsert_asset_vector

logger = logging.getLogger(__name__)


def sync_style_learning_to_memory(db: Session, ip_id: str, text: str) -> Optional[str]:
    """
    为单条学习要点创建 IPAsset 并写入向量（与素材入库同链路）。
    成功返回 asset_id；失败返回 None（不抛异常，避免阻断主流程）。
    """
    t = (text or "").strip()
    if len(t) < 4:
        return None

    asset_id = f"sl_{uuid.uuid4().hex[:20]}"
    if len(asset_id) > 64:
        asset_id = asset_id[:64]

    try:
        row = IPAsset(
            asset_id=asset_id,
            ip_id=ip_id,
            asset_type="text",
            title="文案学习要点（用户反馈）",
            content=t[:8000],
            asset_meta={
                "source": "style_learning",
                "kind": "user_iteration",
            },
            relations=[],
            status="active",
        )
        db.add(row)

        ok = qdrant_upsert_asset_vector(
            db,
            asset_id=asset_id,
            ip_id=ip_id,
            content=t[:8000],
            metadata={
                "source": "style_learning",
                "kind": "user_iteration",
                "title": "文案学习要点",
            },
        )
        if not ok:
            db.rollback()
            return None
        # qdrant_upsert 内部已 db.commit，会一并提交 IPAsset
        return asset_id
    except Exception as e:
        logger.warning("sync_style_learning_to_memory failed: %s", e, exc_info=False)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def sync_style_learning_after_commit(ip_id: str, text: str) -> None:
    """在 strategy_config 已提交后调用，使用独立会话写入向量，避免与上层事务纠缠。"""
    from app.db import SessionLocal

    t = (text or "").strip()
    if len(t) < 4:
        return
    s = SessionLocal()
    try:
        aid = sync_style_learning_to_memory(s, ip_id, t)
        if aid:
            logger.info("style learning synced to memory: ip=%s asset=%s", ip_id, aid)
    finally:
        s.close()
