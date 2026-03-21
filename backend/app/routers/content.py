"""
内容生成API路由 - 三大场景
场景一：热点选题 + 匹配度排序 + 一键生成
场景二：竞品爆款分析 + 改写生成
场景三：自定义原创 + IP风格 + 爆款逻辑
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP
from app.services.content_scenario import (
    ContentGenerator,
    ScenarioOneRequest,
    ScenarioTwoRequest,
    ScenarioThreeRequest,
    FourDimWeights,
    ContentResult,
)

router = APIRouter()


# ==================== 请求模型 ====================

class ScenarioOneRequestAPI(BaseModel):
    """场景一请求"""
    ip_id: str
    platform: str = "all"
    # 四维权重
    weight_relevance: float = Field(0.3, description="相关度权重")
    weight_hotness: float = Field(0.3, description="热度权重")
    weight_competition: float = Field(0.2, description="竞争度权重")
    weight_conversion: float = Field(0.2, description="转化率权重")
    count: int = Field(5, description="生成数量")


class ScenarioTwoRequestAPI(BaseModel):
    """场景二请求"""
    ip_id: str
    competitor_content: str
    competitor_platform: Optional[str] = None
    rewrite_level: str = "medium"


class ScenarioThreeRequestAPI(BaseModel):
    """场景三请求"""
    ip_id: str
    topic: str
    style_profile: Optional[dict] = None
    key_points: Optional[List[str]] = None
    length: str = "medium"


# ==================== 响应模型 ====================

class ContentResultResponse(BaseModel):
    content: str
    score: float
    scenario: str
    metadata: dict


# ==================== 辅助函数 ====================

def get_ip_profile(db: Session, ip_id: str) -> dict:
    """获取IP画像"""
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail=f"IP不存在: {ip_id}")
    
    return {
        "ip_id": ip.ip_id,
        "name": ip.name,
        "expertise": ip.expertise or "",
        "content_direction": ip.content_direction or "",
        "target_audience": ip.target_audience or "",
    }


# ==================== API端点 ====================

@router.post("/scenario/one", response_model=List[ContentResultResponse])
async def generate_scenario_one(
    payload: ScenarioOneRequestAPI,
    db: Session = Depends(get_db),
):
    """
    场景一：热点选题 + 匹配度排序 + 一键生成
    
    流程：
    1. 接入热点话题
    2. 根据四维权重计算匹配度
    3. 排序选题
    4. 一键生成内容
    """
    # 获取IP画像
    ip_profile = get_ip_profile(db, payload.ip_id)
    
    # 构建请求
    weights = FourDimWeights(
        relevance=payload.weight_relevance,
        hotness=payload.weight_hotness,
        competition=payload.weight_competition,
        conversion=payload.weight_conversion,
    )
    
    request = ScenarioOneRequest(
        ip_id=payload.ip_id,
        platform=payload.platform,
        ip_profile=ip_profile,
        weights=weights,
        count=payload.count,
    )
    
    # 生成
    results = await ContentGenerator.scenario_one(request)
    
    return [ContentResultResponse(
        content=r.content,
        score=r.score,
        scenario=r.scenario,
        metadata=r.metadata,
    ) for r in results]


@router.post("/scenario/two", response_model=ContentResultResponse)
async def generate_scenario_two(
    payload: ScenarioTwoRequestAPI,
    db: Session = Depends(get_db),
):
    """
    场景二：竞品爆款改写
    
    流程：
    1. 分析竞品爆款结构
    2. 提取核心要素
    3. IP风格改写
    4. 质量评分
    """
    ip_profile = get_ip_profile(db, payload.ip_id)
    
    request = ScenarioTwoRequest(
        ip_id=payload.ip_id,
        competitor_content=payload.competitor_content,
        competitor_platform=payload.competitor_platform,
        ip_profile=ip_profile,
        rewrite_level=payload.rewrite_level,
    )
    
    result = await ContentGenerator.scenario_two(request)
    
    return ContentResultResponse(
        content=result.content,
        score=result.score,
        scenario=result.scenario,
        metadata=result.metadata,
    )


@router.post("/scenario/three", response_model=ContentResultResponse)
async def generate_scenario_three(
    payload: ScenarioThreeRequestAPI,
    db: Session = Depends(get_db),
):
    """
    场景三：自定义原创
    
    流程：
    1. 用户输入话题
    2. 应用IP风格
    3. 运用爆款逻辑
    4. 生成内容
    """
    ip_profile = get_ip_profile(db, payload.ip_id)
    
    request = ScenarioThreeRequest(
        ip_id=payload.ip_id,
        topic=payload.topic,
        style_profile=payload.style_profile,
        key_points=payload.key_points,
        length=payload.length,
    )
    
    result = await ContentGenerator.scenario_three(request)
    
    return ContentResultResponse(
        content=result.content,
        score=result.score,
        scenario=result.scenario,
        metadata=result.metadata,
    )


# ==================== 便捷测试端点 ====================

@router.get("/scenario/test")
async def test_scenarios():
    """测试端点，返回场景说明"""
    return {
        "scenarios": {
            "scenario_1": {
                "name": "热点选题生成",
                "description": "接入热点 + 四维匹配度排序 + 一键生成",
                "params": ["ip_id", "platform", "weights", "count"],
            },
            "scenario_2": {
                "name": "竞品改写",
                "description": "分析爆款结构 + IP风格改写",
                "params": ["ip_id", "competitor_content", "rewrite_level"],
            },
            "scenario_3": {
                "name": "自定义原创",
                "description": "自定义话题 + IP风格 + 爆款逻辑",
                "params": ["ip_id", "topic", "style_profile", "length"],
            },
        }
    }
