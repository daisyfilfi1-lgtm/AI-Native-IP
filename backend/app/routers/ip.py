from typing import List, Optional

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
    
    # 账号体系：超级符号识别系统（2个核心触点）
    nickname: Optional[str] = None
    bio: Optional[str] = None
    
    # 商业定位：变现前置原则
    monetization_model: Optional[str] = None
    target_audience: Optional[str] = None
    content_direction: Optional[str] = None
    unique_value_prop: Optional[str] = None
    
    # 定位交叉点：擅长 × 热爱 × 市场需求
    expertise: Optional[str] = None
    passion: Optional[str] = None
    market_demand: Optional[str] = None
    
    # 变现象限：产品/服务 × 客单价 × 复购率
    product_service: Optional[str] = None
    price_range: Optional[str] = None
    repurchase_rate: Optional[str] = None


class CreateIPRequest(BaseModel):
    ip_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    owner_user_id: str = Field(..., min_length=1, max_length=64)
    status: str = Field(default="active", max_length=32)
    
    # 账号体系字段
    nickname: Optional[str] = Field(default=None, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    
    # 商业定位字段
    monetization_model: Optional[str] = Field(default=None, max_length=50)
    target_audience: Optional[str] = Field(default=None, max_length=255)
    content_direction: Optional[str] = Field(default=None, max_length=255)
    unique_value_prop: Optional[str] = Field(default=None, max_length=500)
    
    # 定位交叉点字段
    expertise: Optional[str] = Field(default=None, max_length=255)
    passion: Optional[str] = Field(default=None, max_length=255)
    market_demand: Optional[str] = Field(default=None, max_length=255)
    
    # 变现象限字段
    product_service: Optional[str] = Field(default=None, max_length=255)
    price_range: Optional[str] = Field(default=None, max_length=100)
    repurchase_rate: Optional[str] = Field(default=None, max_length=50)


def ip_to_response(row: IP) -> IPResponse:
    """将数据库IP模型转换为响应模型"""
    return IPResponse(
        ip_id=row.ip_id,
        name=row.name,
        owner_user_id=row.owner_user_id,
        status=row.status,
        # 账号体系
        nickname=row.nickname,
        bio=row.bio,
        # 商业定位
        monetization_model=row.monetization_model,
        target_audience=row.target_audience,
        content_direction=row.content_direction,
        unique_value_prop=row.unique_value_prop,
        # 定位交叉点
        expertise=row.expertise,
        passion=row.passion,
        market_demand=row.market_demand,
        # 变现象限
        product_service=row.product_service,
        price_range=row.price_range,
        repurchase_rate=row.repurchase_rate,
    )


@router.get("/ip", response_model=List[IPResponse])
def list_ips(db: Session = Depends(get_db)):
    """列出所有 IP（按创建时间倒序）。"""
    rows = db.query(IP).order_by(IP.created_at.desc()).all()
    return [ip_to_response(r) for r in rows]


@router.post("/ip", response_model=IPResponse, status_code=201)
def create_ip(payload: CreateIPRequest, db: Session = Depends(get_db)):
    """
    创建 IP。ip_id 需全局唯一，若已存在返回 409。
    支持完整的账号体系字段和商业定位信息。
    """
    if get_ip(db, payload.ip_id):
        raise HTTPException(status_code=409, detail=f"IP 已存在: {payload.ip_id}")
    
    row = IP(
        ip_id=payload.ip_id,
        name=payload.name,
        owner_user_id=payload.owner_user_id,
        status=payload.status,
        # 账号体系
        nickname=payload.nickname,
        bio=payload.bio,
        # 商业定位
        monetization_model=payload.monetization_model,
        target_audience=payload.target_audience,
        content_direction=payload.content_direction,
        unique_value_prop=payload.unique_value_prop,
        # 定位交叉点
        expertise=payload.expertise,
        passion=payload.passion,
        market_demand=payload.market_demand,
        # 变现象限
        product_service=payload.product_service,
        price_range=payload.price_range,
        repurchase_rate=payload.repurchase_rate,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ip_to_response(row)


@router.get("/ip/{ip_id}", response_model=IPResponse)
def get_ip_by_id(ip_id: str, db: Session = Depends(get_db)):
    """查询单个 IP。"""
    row = get_ip(db, ip_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    return ip_to_response(row)


@router.delete("/ip/{ip_id}")
def delete_ip(ip_id: str, db: Session = Depends(get_db)):
    """
    删除 IP 及其关联数据（素材、向量、配置、任务、竞品等）。
    不可恢复，请前端二次确认后再调用。
    """
    from app.services.ip_delete_service import delete_ip_and_related

    ok = delete_ip_and_related(db, ip_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    return {"success": True, "ip_id": ip_id}
