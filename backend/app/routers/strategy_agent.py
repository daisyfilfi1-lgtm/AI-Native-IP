"""
策略 Agent API：评分卡权重 / 抓取配置（ip.strategy_config）与竞品监控（competitor_accounts）
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import CompetitorAccount, IP
from app.services.strategy_config_service import (
    get_merged_config,
    merge_strategy_config,
    scorecard_total,
)

router = APIRouter()


# ----- 策略配置 -----


class StrategyConfigPut(BaseModel):
    ip_id: str = Field(..., description="IP ID")
    four_dim_weights: Optional[dict] = None
    scorecard_sliders: Optional[dict] = None
    shoot_threshold: Optional[int] = Field(None, ge=0, le=10)
    topic_blacklist: Optional[List[str]] = None
    crawl: Optional[dict] = None


class StrategyConfigResponse(BaseModel):
    four_dim_weights: dict
    scorecard_sliders: dict
    shoot_threshold: int
    topic_blacklist: List[str]
    crawl: dict
    scorecard_total: int
    shoot_recommendation: str


@router.get("/strategy/config", response_model=StrategyConfigResponse)
def get_strategy_config(
    ip_id: str = Query(..., description="IP ID"),
    db: Session = Depends(get_db),
):
    if not db.query(IP).filter(IP.ip_id == ip_id).first():
        raise HTTPException(status_code=404, detail=f"IP不存在: {ip_id}")
    data = get_merged_config(db, ip_id)
    return StrategyConfigResponse(**data)


@router.put("/strategy/config", response_model=StrategyConfigResponse)
def put_strategy_config(
    payload: StrategyConfigPut,
    db: Session = Depends(get_db),
):
    ip = db.query(IP).filter(IP.ip_id == payload.ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")

    existing = ip.strategy_config if isinstance(ip.strategy_config, dict) else {}
    patch = {**existing}
    if payload.four_dim_weights is not None:
        patch["four_dim_weights"] = payload.four_dim_weights
    if payload.scorecard_sliders is not None:
        patch["scorecard_sliders"] = payload.scorecard_sliders
    if payload.shoot_threshold is not None:
        patch["shoot_threshold"] = payload.shoot_threshold
    if payload.topic_blacklist is not None:
        patch["topic_blacklist"] = payload.topic_blacklist
    if payload.crawl is not None:
        patch["crawl"] = payload.crawl

    merged = merge_strategy_config(patch)
    ip.strategy_config = merged
    ip.updated_at = datetime.utcnow()
    db.add(ip)
    db.commit()
    db.refresh(ip)

    out = merge_strategy_config(ip.strategy_config if isinstance(ip.strategy_config, dict) else None)
    out["scorecard_total"] = scorecard_total(out["scorecard_sliders"])
    out["shoot_recommendation"] = (
        "可拍摄" if out["scorecard_total"] >= out["shoot_threshold"] else "待评估"
    )
    return StrategyConfigResponse(**out)


# ----- 竞品监控 -----


class CompetitorCreate(BaseModel):
    ip_id: str
    name: str = Field(..., min_length=1, max_length=255)
    platform: str = Field("", max_length=64)
    followers_display: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = None


class CompetitorPatch(BaseModel):
    ip_id: str
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    platform: Optional[str] = Field(None, max_length=64)
    followers_display: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = None


class CompetitorOut(BaseModel):
    competitor_id: str
    ip_id: str
    name: str
    platform: str
    followers_display: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompetitorListResponse(BaseModel):
    items: List[CompetitorOut]


def _get_competitor_or_404(db: Session, ip_id: str, competitor_id: str) -> CompetitorAccount:
    row = (
        db.query(CompetitorAccount)
        .filter(CompetitorAccount.competitor_id == competitor_id, CompetitorAccount.ip_id == ip_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="竞品记录不存在")
    return row


@router.get("/strategy/competitors", response_model=CompetitorListResponse)
def list_competitors(
    ip_id: str = Query(...),
    db: Session = Depends(get_db),
):
    if not db.query(IP).filter(IP.ip_id == ip_id).first():
        raise HTTPException(status_code=404, detail=f"IP不存在: {ip_id}")
    rows = (
        db.query(CompetitorAccount)
        .filter(CompetitorAccount.ip_id == ip_id)
        .order_by(CompetitorAccount.created_at.desc())
        .all()
    )
    return CompetitorListResponse(
        items=[
            CompetitorOut(
                competitor_id=r.competitor_id,
                ip_id=r.ip_id,
                name=r.name,
                platform=r.platform or "",
                followers_display=r.followers_display,
                notes=r.notes,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]
    )


@router.post("/strategy/competitors", response_model=CompetitorOut)
def create_competitor(
    payload: CompetitorCreate,
    db: Session = Depends(get_db),
):
    if not db.query(IP).filter(IP.ip_id == payload.ip_id).first():
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")
    cid = uuid.uuid4().hex[:16]
    now = datetime.utcnow()
    row = CompetitorAccount(
        competitor_id=cid,
        ip_id=payload.ip_id,
        name=payload.name.strip(),
        platform=(payload.platform or "").strip(),
        followers_display=(payload.followers_display or "").strip() or None,
        notes=payload.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CompetitorOut(
        competitor_id=row.competitor_id,
        ip_id=row.ip_id,
        name=row.name,
        platform=row.platform or "",
        followers_display=row.followers_display,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.patch("/strategy/competitors/{competitor_id}", response_model=CompetitorOut)
def patch_competitor(
    competitor_id: str,
    payload: CompetitorPatch,
    db: Session = Depends(get_db),
):
    row = _get_competitor_or_404(db, payload.ip_id, competitor_id)
    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.platform is not None:
        row.platform = payload.platform.strip()
    if payload.followers_display is not None:
        v = payload.followers_display.strip()
        row.followers_display = v or None
    if payload.notes is not None:
        row.notes = payload.notes
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return CompetitorOut(
        competitor_id=row.competitor_id,
        ip_id=row.ip_id,
        name=row.name,
        platform=row.platform or "",
        followers_display=row.followers_display,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.delete("/strategy/competitors/{competitor_id}")
def delete_competitor(
    competitor_id: str,
    ip_id: str = Query(...),
    db: Session = Depends(get_db),
):
    row = _get_competitor_or_404(db, ip_id, competitor_id)
    db.delete(row)
    db.commit()
    return {"success": True}
