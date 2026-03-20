from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP
from app.services.memory_config_service import get_ip

router = APIRouter()


class IPResponse(BaseModel):
    ip_id: str
    name: str
    owner_user_id: str
    status: str


class CreateIPRequest(BaseModel):
    ip_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    owner_user_id: str = Field(..., min_length=1, max_length=64)
    status: str = Field(default="active", max_length=32)


@router.get("/ip", response_model=List[IPResponse])
def list_ips(db: Session = Depends(get_db)):
    """列出所有 IP（按创建时间倒序）。"""
    rows = db.query(IP).order_by(IP.created_at.desc()).all()
    return [
        IPResponse(ip_id=r.ip_id, name=r.name, owner_user_id=r.owner_user_id, status=r.status)
        for r in rows
    ]


@router.post("/ip", response_model=IPResponse, status_code=201)
def create_ip(payload: CreateIPRequest, db: Session = Depends(get_db)):
    """
    创建 IP。ip_id 需全局唯一，若已存在返回 409。
    """
    if get_ip(db, payload.ip_id):
        raise HTTPException(status_code=409, detail=f"IP 已存在: {payload.ip_id}")
    row = IP(
        ip_id=payload.ip_id,
        name=payload.name,
        owner_user_id=payload.owner_user_id,
        status=payload.status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return IPResponse(
        ip_id=row.ip_id,
        name=row.name,
        owner_user_id=row.owner_user_id,
        status=row.status,
    )


@router.get("/ip/{ip_id}", response_model=IPResponse)
def get_ip_by_id(ip_id: str, db: Session = Depends(get_db)):
    """查询单个 IP。"""
    row = get_ip(db, ip_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    return IPResponse(
        ip_id=row.ip_id,
        name=row.name,
        owner_user_id=row.owner_user_id,
        status=row.status,
    )
