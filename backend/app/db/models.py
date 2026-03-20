from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def now_utc() -> datetime:
    return datetime.utcnow()


class IP(Base):
    __tablename__ = "ip"

    ip_id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    owner_user_id = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)


class IPAsset(Base):
    __tablename__ = "ip_assets"

    asset_id = Column(String(64), primary_key=True)
    ip_id = Column(String(64), ForeignKey("ip.ip_id"), nullable=False, index=True)
    asset_type = Column(String(32), nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    content_vector_ref = Column(String(128), nullable=True)
    asset_meta = Column("metadata", JSONB, nullable=False, default=dict)  # 列名 metadata，避免与 DeclarativeBase.metadata 冲突
    relations = Column(JSONB, nullable=False, default=list)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)

    __table_args__ = (Index("idx_ip_assets_metadata_gin", "metadata", postgresql_using="gin"),)


class TagConfig(Base):
    __tablename__ = "tag_config"

    config_id = Column(String(64), primary_key=True)
    ip_id = Column(String(64), ForeignKey("ip.ip_id"), nullable=False, unique=True)
    tag_categories = Column(JSONB, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_by = Column(String(64), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)


class MemoryConfig(Base):
    __tablename__ = "memory_config"

    config_id = Column(String(64), primary_key=True)
    ip_id = Column(String(64), ForeignKey("ip.ip_id"), nullable=False, unique=True)
    retrieval = Column(JSONB, nullable=False)
    usage_limits = Column(JSONB, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_by = Column(String(64), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)


class ConfigHistory(Base):
    __tablename__ = "config_history"

    id = Column(String(64), primary_key=True)
    ip_id = Column(String(64), nullable=False, index=True)
    agent_type = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    config_json = Column(JSONB, nullable=False)
    changed_by = Column(String(64), nullable=False)
    changed_at = Column(DateTime, nullable=False, default=now_utc)

    __table_args__ = (
        Index("idx_config_history_ip_agent", "ip_id", "agent_type"),
    )


class IngestTask(Base):
    __tablename__ = "ingest_tasks"

    task_id = Column(String(64), primary_key=True)
    ip_id = Column(String(64), ForeignKey("ip.ip_id"), nullable=False, index=True)
    source_type = Column(String(32), nullable=False)
    source_url = Column(String(2048), nullable=True)
    local_file_id = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="QUEUED")
    error_message = Column(Text, nullable=True)
    created_asset_ids = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)


class IntegrationConfig(Base):
    __tablename__ = "integration_config"

    key = Column(String(64), primary_key=True)
    value_json = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)


class FileObject(Base):
    __tablename__ = "file_objects"

    file_id = Column(String(64), primary_key=True)
    ip_id = Column(String(64), ForeignKey("ip.ip_id"), nullable=False, index=True)
    provider = Column(String(32), nullable=False, default="s3")
    bucket = Column(String(255), nullable=False)
    object_key = Column(String(1024), nullable=False)
    file_name = Column(String(255), nullable=True)
    content_type = Column(String(128), nullable=True)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    etag = Column(String(128), nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)

    __table_args__ = (
        Index("idx_file_objects_bucket_key", "bucket", "object_key", unique=True),
    )


class AssetVector(Base):
    __tablename__ = "asset_vectors"

    asset_id = Column(String(64), ForeignKey("ip_assets.asset_id"), primary_key=True)
    ip_id = Column(String(64), ForeignKey("ip.ip_id"), nullable=False, index=True)
    embedding = Column(JSONB, nullable=False)
    dim = Column(Integer, nullable=False)
    model = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)


class ContentDraft(Base):
    __tablename__ = "content_drafts"

    draft_id = Column(String(64), primary_key=True)
    ip_id = Column(String(64), ForeignKey("ip.ip_id"), nullable=False, index=True)
    level = Column(String(8), nullable=False)
    workflow = Column(JSONB, nullable=False)
    quality_score = Column(JSONB, nullable=False)
    compliance_status = Column(String(32), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)
