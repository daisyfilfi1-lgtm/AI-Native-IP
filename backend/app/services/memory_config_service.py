"""
Memory 配置的数据库 CRUD，供 config_memory 路由使用。
"""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import ConfigHistory, IP, MemoryConfig, TagConfig


def get_ip(db: Session, ip_id: str) -> Optional[IP]:
    return db.query(IP).filter(IP.ip_id == ip_id).first()


def get_tag_config(db: Session, ip_id: str) -> Optional[TagConfig]:
    return db.query(TagConfig).filter(TagConfig.ip_id == ip_id).first()


def get_memory_config_row(db: Session, ip_id: str) -> Optional[MemoryConfig]:
    return db.query(MemoryConfig).filter(MemoryConfig.ip_id == ip_id).first()


def upsert_tag_config(
    db: Session,
    config_id: str,
    ip_id: str,
    tag_categories: list,
    updated_by: str,
) -> TagConfig:
    row = get_tag_config(db, ip_id)
    if row:
        row.config_id = config_id
        row.tag_categories = tag_categories
        row.version = row.version + 1
        row.updated_by = updated_by
        db.flush()
        return row
    row = TagConfig(
        config_id=config_id,
        ip_id=ip_id,
        tag_categories=tag_categories,
        version=1,
        updated_by=updated_by,
    )
    db.add(row)
    db.flush()
    return row


def upsert_memory_config(
    db: Session,
    config_id: str,
    ip_id: str,
    retrieval: dict,
    usage_limits: dict,
    updated_by: str,
) -> MemoryConfig:
    row = get_memory_config_row(db, ip_id)
    if row:
        row.config_id = config_id
        row.retrieval = retrieval
        row.usage_limits = usage_limits
        row.version = row.version + 1
        row.updated_by = updated_by
        db.flush()
        return row
    row = MemoryConfig(
        config_id=config_id,
        ip_id=ip_id,
        retrieval=retrieval,
        usage_limits=usage_limits,
        version=1,
        updated_by=updated_by,
    )
    db.add(row)
    db.flush()
    return row


def append_config_history(
    db: Session,
    ip_id: str,
    agent_type: str,
    version: int,
    config_json: dict,
    changed_by: str,
) -> None:
    db.add(
        ConfigHistory(
            id=uuid.uuid4().hex,
            ip_id=ip_id,
            agent_type=agent_type,
            version=version,
            config_json=config_json,
            changed_by=changed_by,
        )
    )
