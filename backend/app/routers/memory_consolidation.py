"""
记忆Consolidation路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.memory_config_service import get_ip as get_ip_model
from app.services.memory_consolidation_service import (
    MemoryConsolidation,
    consolidate_ip_memory,
    get_memory_summary,
)

router = APIRouter()


class ConsolidateResponse(BaseModel):
    total_assets: int
    promoted: int
    demoted: int
    archived: int
    core_summary: Optional[str] = None


class MemorySummaryResponse(BaseModel):
    stats: dict
    core_memory: list
    archived_memory: list


class CoreMemoryResponse(BaseModel):
    items: list


class RestoreArchiveRequest(BaseModel):
    asset_id: str


class TimeWeightedRequest(BaseModel):
    ip_id: str
    query: str
    top_k: Optional[int] = 10
    time_weight: Optional[float] = 0.3


@router.post("/memory/consolidate", response_model=ConsolidateResponse)
def consolidate_memory(
    ip_id: str,
    db: Session = Depends(get_db),
):
    """
    执行记忆Consolidation
    
    1. 统计使用情况
    2. 调整记忆级别（核心/活跃/归档）
    3. 提炼核心知识摘要
    4. 归档冷门内容
    """
    if not get_ip_model(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    
    result = consolidate_ip_memory(db, ip_id)
    return ConsolidateResponse(**result)


@router.get("/memory/summary", response_model=MemorySummaryResponse)
def get_summary(
    ip_id: str,
    db: Session = Depends(get_db),
):
    """获取IP的记忆摘要"""
    if not get_ip_model(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    
    return get_memory_summary(db, ip_id)


@router.get("/memory/core", response_model=CoreMemoryResponse)
def get_core_memory(
    ip_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """获取核心记忆列表"""
    if not get_ip_model(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    
    engine = MemoryConsolidation(db, ip_id)
    items = engine.get_core_memory(limit=limit)
    
    return CoreMemoryResponse(items=items)


@router.get("/memory/archived", response_model=CoreMemoryResponse)
def get_archived_memory(
    ip_id: str,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """获取归档记忆列表"""
    if not get_ip_model(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    
    engine = MemoryConsolidation(db, ip_id)
    items = engine.get_archived_memory(limit=limit)
    
    return CoreMemoryResponse(items=items)


@router.post("/memory/restore")
def restore_from_archive(
    ip_id: str,
    payload: RestoreArchiveRequest,
    db: Session = Depends(get_db),
):
    """从归档恢复记忆"""
    if not get_ip_model(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    
    engine = MemoryConsolidation(db, ip_id)
    success = engine.restore_from_archive(payload.asset_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"素材不存在: {payload.asset_id}")
    
    return {"success": True, "message": "已从归档恢复"}


@router.post("/memory/retrieve/time-weighted")
def retrieve_time_weighted(
    payload: TimeWeightedRequest,
    db: Session = Depends(get_db),
):
    """
    时间加权检索
    
    最近使用的记忆权重更高，结合使用频率和记忆级别综合排序
    """
    if not get_ip_model(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    
    engine = MemoryConsolidation(db, payload.ip_id)
    
    results = engine.time_weighted_retrieval(
        query=payload.query,
        top_k=payload.top_k or 10,
        time_weight=payload.time_weight or 0.3,
    )
    
    return {
        "query": payload.query,
        "total": len(results),
        "results": [
            {
                "asset_id": r["asset_id"],
                "title": r["title"],
                "content_snippet": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
                "score": round(r["score"], 3),
                "level": r["level"],
                "time_score": round(r["time_score"], 3),
                "usage_score": round(r["usage_score"], 3),
            }
            for r in results
        ],
    }
