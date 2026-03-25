"""
IP风格建模API路由
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP, IPAsset
from app.services.style_modeling import (
    IPStyleProfile,
    extract_style_from_assets,
    apply_style,
    generate_with_style,
)

router = APIRouter()


# ==================== 请求/响应模型 ====================

class ExtractStyleRequest(BaseModel):
    ip_id: str
    asset_count: Optional[int] = Field(50, description="用于提取的素材数量")


class ApplyStyleRequest(BaseModel):
    ip_id: str
    content: str = Field(..., description="要转换风格的内容")


class GenerateWithStyleRequest(BaseModel):
    ip_id: str
    topic: str = Field(..., description="生成内容的话题")


class StyleTextResponse(BaseModel):
    content: str


class StyleProfileResponse(BaseModel):
    ip_id: str
    vocabulary: List[str]
    sentence_patterns: List[str]
    emotion_curve: str
    catchphrases: List[str]
    tone: str
    topics: List[str]
    length_preference: str
    format_preference: str
    humor_style: Optional[str] = None
    formality: Optional[float] = None
    emotion_density: Optional[float] = None


# ==================== API端点 ====================

@router.post("/style/extract", response_model=StyleProfileResponse)
async def extract_style(
    payload: ExtractStyleRequest,
    db: Session = Depends(get_db),
):
    """
    提取IP风格特征
    
    从IP的历史素材中自动提取风格特征，构建风格画像
    """
    # 验证IP存在
    ip = db.query(IP).filter(IP.ip_id == payload.ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")
    
    # 获取素材
    assets = db.query(IPAsset).filter(
        IPAsset.ip_id == payload.ip_id
    ).limit(payload.asset_count).all()
    
    if not assets:
        raise HTTPException(status_code=400, detail="没有找到素材，请先录入素材")
    
    # 转换为dict
    asset_list = [
        {"content": a.content, "type": a.asset_type}
        for a in assets
    ]
    
    # 提取风格
    profile = extract_style_from_assets(asset_list, payload.ip_id)
    data = profile.model_dump()
    ip.style_profile = data
    ip.updated_at = datetime.utcnow()
    db.add(ip)
    db.commit()
    db.refresh(ip)

    return StyleProfileResponse(**data)


@router.post("/style/apply", response_model=StyleTextResponse)
async def apply_ip_style(
    payload: ApplyStyleRequest,
    db: Session = Depends(get_db),
):
    """
    应用IP风格
    
    将已有内容转换为IP风格
    """
    ip = db.query(IP).filter(IP.ip_id == payload.ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")
    if not ip.style_profile:
        raise HTTPException(status_code=400, detail="请先调用 POST /style/extract 从素材提取风格")

    profile = IPStyleProfile.model_validate(dict(ip.style_profile))
    text = apply_style(payload.content, profile)
    return StyleTextResponse(content=text)


@router.post("/style/generate", response_model=StyleTextResponse)
async def generate_with_ip_style(
    payload: GenerateWithStyleRequest,
    db: Session = Depends(get_db),
):
    """
    带风格生成内容
    
    基于IP风格画像生成内容
    """
    ip = db.query(IP).filter(IP.ip_id == payload.ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")
    if not ip.style_profile:
        raise HTTPException(status_code=400, detail="请先调用 POST /style/extract 从素材提取风格")

    profile = IPStyleProfile.model_validate(dict(ip.style_profile))
    text = generate_with_style(payload.topic, profile)
    return StyleTextResponse(content=text)


@router.get("/style/{ip_id}", response_model=StyleProfileResponse)
async def get_style_profile(
    ip_id: str,
    db: Session = Depends(get_db),
):
    """
    获取IP风格画像
    """
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail=f"IP不存在: {ip_id}")
    if not ip.style_profile:
        raise HTTPException(status_code=404, detail="风格画像未提取，请先调用 /style/extract")

    return StyleProfileResponse(**dict(ip.style_profile))
