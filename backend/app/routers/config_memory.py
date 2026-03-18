from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.memory_config_service import (
    append_config_history,
    get_ip,
    get_memory_config_row,
    get_tag_config,
    upsert_memory_config,
    upsert_tag_config,
)

router = APIRouter()


class TagCategoryValue(BaseModel):
    value: str
    label: str
    color: str
    enabled: bool = True


class TagCategory(BaseModel):
    name: str
    level: int
    type: str
    values: list[TagCategoryValue]


class TagConfigSchema(BaseModel):
    config_id: str
    ip_id: str
    tag_categories: list[TagCategory]
    version: int
    updated_by: str
    updated_at: str


class RetrievalConfig(BaseModel):
    strategy: str
    top_k: int
    min_similarity: float
    diversity_enabled: bool
    diversity_recent_window: int
    freshness_weight: int


class UsageLimitsConfig(BaseModel):
    core_max_usage: int
    normal_max_usage: int
    disposable_max_usage: int
    exceed_behavior: str


class MemoryConfigSchema(BaseModel):
    config_id: str
    ip_id: str
    retrieval: RetrievalConfig
    usage_limits: UsageLimitsConfig
    version: int
    updated_by: str
    updated_at: str


class MemoryFullConfig(BaseModel):
    tag_config: TagConfigSchema | None = None
    memory_config: MemoryConfigSchema | None = None


def _tag_row_to_schema(row: Any) -> TagConfigSchema:
    return TagConfigSchema(
        config_id=row.config_id,
        ip_id=row.ip_id,
        tag_categories=row.tag_categories,
        version=row.version,
        updated_by=row.updated_by,
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


def _memory_row_to_schema(row: Any) -> MemoryConfigSchema:
    return MemoryConfigSchema(
        config_id=row.config_id,
        ip_id=row.ip_id,
        retrieval=row.retrieval,
        usage_limits=row.usage_limits,
        version=row.version,
        updated_by=row.updated_by,
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


@router.get("/config/memory", response_model=MemoryFullConfig)
def get_memory_config(ip_id: str, db: Session = Depends(get_db)) -> Any:
    """
    读取 Memory 相关配置（标签 + 检索/使用限制）。
    若该 IP 尚无配置则返回 tag_config / memory_config 均为 null。
    """
    tag_row = get_tag_config(db, ip_id)
    memory_row = get_memory_config_row(db, ip_id)
    return MemoryFullConfig(
        tag_config=_tag_row_to_schema(tag_row) if tag_row else None,
        memory_config=_memory_row_to_schema(memory_row) if memory_row else None,
    )


@router.post("/config/memory")
def save_memory_config(
    payload: MemoryFullConfig,
    db: Session = Depends(get_db),
) -> Any:
    """
    保存 Memory 相关配置（可只提交 tag_config 或 memory_config 其一）。
    会写入 config_history 便于回滚。
    """
    if not payload.tag_config and not payload.memory_config:
        raise HTTPException(
            status_code=400,
            detail="至少需要提供 tag_config 或 memory_config 之一",
        )

    ip_id = (
        payload.tag_config.ip_id if payload.tag_config else payload.memory_config.ip_id
    )
    if not get_ip(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")

    updated_by = "system"
    if payload.tag_config:
        updated_by = payload.tag_config.updated_by
    if payload.memory_config:
        updated_by = payload.memory_config.updated_by

    version = 1
    config_json: dict = {}

    if payload.tag_config:
        tc = payload.tag_config
        tag_categories = [c.model_dump() for c in tc.tag_categories]
        row = upsert_tag_config(
            db,
            config_id=tc.config_id,
            ip_id=tc.ip_id,
            tag_categories=tag_categories,
            updated_by=tc.updated_by,
        )
        version = max(version, row.version)
        config_json["tag_config"] = payload.tag_config.model_dump()

    if payload.memory_config:
        mc = payload.memory_config
        row = upsert_memory_config(
            db,
            config_id=mc.config_id,
            ip_id=mc.ip_id,
            retrieval=mc.retrieval.model_dump(),
            usage_limits=mc.usage_limits.model_dump(),
            updated_by=mc.updated_by,
        )
        version = max(version, row.version)
        config_json["memory_config"] = payload.memory_config.model_dump()

    append_config_history(
        db,
        ip_id=payload.tag_config.ip_id if payload.tag_config else payload.memory_config.ip_id,
        agent_type="memory",
        version=version,
        config_json=config_json,
        changed_by=updated_by,
    )
    db.commit()
    return {"success": True, "version": version}
