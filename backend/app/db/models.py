from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
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
    
    # 账号体系：超级符号识别系统（2个核心触点）
    nickname = Column(String(100), nullable=True)  # 昵称
    bio = Column(String(500), nullable=True)  # 简介
    
    # 商业定位：变现前置原则
    monetization_model = Column(String(50), nullable=True)  # 变现模式
    target_audience = Column(String(255), nullable=True)  # 目标受众
    content_direction = Column(String(255), nullable=True)  # 内容方向
    unique_value_prop = Column(String(500), nullable=True)  # 独特价值主张
    
    # 定位交叉点：擅长 × 热爱 × 市场需求
    expertise = Column(String(255), nullable=True)  # 擅长领域
    passion = Column(String(255), nullable=True)  # 热爱领域
    market_demand = Column(String(255), nullable=True)  # 市场需求
    
    # 变现象限：产品/服务 × 客单价 × 复购率
    product_service = Column(String(255), nullable=True)  # 产品/服务
    price_range = Column(String(100), nullable=True)  # 客单价区间
    repurchase_rate = Column(String(50), nullable=True)  # 复购率

    # 从素材提取的风格画像（JSON，与 IPStyleProfile 字段一致）
    style_profile = Column(JSONB, nullable=True)

    # 策略 Agent：四维权重、选题评分卡滑块、黑名单、抓取配置等
    strategy_config = Column(JSONB, nullable=True)


class CompetitorAccount(Base):
    """竞品监控账号（按 IP 维度）"""

    __tablename__ = "competitor_accounts"

    competitor_id = Column(String(64), primary_key=True)
    ip_id = Column(String(64), ForeignKey("ip.ip_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    platform = Column(String(64), nullable=False, default="")
    followers_display = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
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
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)


class IntegrationConfig(Base):
    __tablename__ = "integration_config"

    key = Column(String(64), primary_key=True)
    value_json = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)


class IntegrationBinding(Base):
    __tablename__ = "integration_bindings"

    id = Column(String(64), primary_key=True)
    integration = Column(String(64), nullable=False, index=True)
    ip_id = Column(String(64), ForeignKey("ip.ip_id"), nullable=False, index=True)
    external_id = Column(String(255), nullable=False)
    external_name = Column(String(255), nullable=True)
    extra = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)

    __table_args__ = (
        Index("uq_integration_ip", "integration", "ip_id", unique=True),
    )


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
    embedding = Column(Vector(1536), nullable=False)
    dim = Column(Integer, nullable=False)
    model = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)


class User(Base):
    """手机号/邮箱 + 密码登录用户"""

    __tablename__ = "users"

    user_id = Column(String(64), primary_key=True)
    phone = Column(String(20), nullable=True, unique=True)
    email = Column(String(128), nullable=True, unique=True)
    password_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, nullable=False, default=now_utc)
    updated_at = Column(DateTime, nullable=False, default=now_utc, onupdate=now_utc)
    last_login_at = Column(DateTime, nullable=True)


class AuthOtp(Base):
    """短信验证码记录（一次性）"""

    __tablename__ = "auth_otp"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False, index=True)
    code_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=now_utc)


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


class RewriteFeedback(Base):
    """用户重写反馈（用于自进化分析）"""
    __tablename__ = "rewrite_feedback"

    feedback_id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    draft_id = Column(String(64), ForeignKey("content_drafts.draft_id"), nullable=False, index=True)
    ip_id = Column(String(64), ForeignKey("ip.ip_id"), nullable=False, index=True)
    user_id = Column(String(64), nullable=True)  # 可选，匿名用户也能反馈
    
    rewrite_reason = Column(String(32), nullable=False)  # 重写原因
    user_comment = Column(Text, nullable=True)  # 用户补充说明
    
    created_at = Column(DateTime, nullable=False, default=now_utc)
