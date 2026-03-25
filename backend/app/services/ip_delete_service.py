"""
删除 IP 及其关联数据（Postgres 外键多为 NO ACTION，需按顺序清理）。
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import (
    AssetVector,
    CompetitorAccount,
    ConfigHistory,
    ContentDraft,
    FileObject,
    IP,
    IPAsset,
    IngestTask,
    IntegrationBinding,
    MemoryConfig,
    TagConfig,
)

logger = logging.getLogger(__name__)


def delete_ip_and_related(db: Session, ip_id: str) -> bool:
    """
    删除指定 ip_id 及其关联行。若 IP 不存在返回 False。
    Neo4j 图谱若已配置则尽力清理，失败不阻断。
    """
    row = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not row:
        return False

    try:
        from app.services.graph_rag_service import clear_ip_graph

        res = clear_ip_graph(ip_id)
        if isinstance(res, dict) and res.get("error"):
            logger.info("clear_ip_graph (non-fatal): %s", res.get("error"))
    except Exception as e:
        logger.info("clear_ip_graph skipped: %s", e)

    # 顺序：先子表（向量依赖素材行）
    db.query(AssetVector).filter(AssetVector.ip_id == ip_id).delete(synchronize_session=False)
    db.query(IPAsset).filter(IPAsset.ip_id == ip_id).delete(synchronize_session=False)

    db.query(TagConfig).filter(TagConfig.ip_id == ip_id).delete(synchronize_session=False)
    db.query(MemoryConfig).filter(MemoryConfig.ip_id == ip_id).delete(synchronize_session=False)
    db.query(IngestTask).filter(IngestTask.ip_id == ip_id).delete(synchronize_session=False)
    db.query(IntegrationBinding).filter(IntegrationBinding.ip_id == ip_id).delete(synchronize_session=False)
    db.query(FileObject).filter(FileObject.ip_id == ip_id).delete(synchronize_session=False)
    db.query(ContentDraft).filter(ContentDraft.ip_id == ip_id).delete(synchronize_session=False)
    db.query(ConfigHistory).filter(ConfigHistory.ip_id == ip_id).delete(synchronize_session=False)
    db.query(CompetitorAccount).filter(CompetitorAccount.ip_id == ip_id).delete(synchronize_session=False)

    try:
        db.query(IP).filter(IP.ip_id == ip_id).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def get_ip_or_none(db: Session, ip_id: str) -> Optional[IP]:
    return db.query(IP).filter(IP.ip_id == ip_id).first()
