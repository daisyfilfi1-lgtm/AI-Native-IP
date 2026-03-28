"""
选题推荐API V4.0 - 基于竞品爆款的智能推荐

核心改进：
- 竞品爆款作为核心数据源
- 内容重构引擎（非模板改写）
- 已被同类IP验证过的选题
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.services.topic_recommendation_v4 import (
    get_recommendation_service_v4,
    RecommendedTopicV4
)

router = APIRouter()


class TopicRecommendationV4Response(BaseModel):
    """V4推荐响应"""
    ip_id: str
    total_count: int
    strategy: str
    topics: list
    competitor_stats: Optional[dict] = None
    
    class Config:
        from_attributes = True


class CompetitorStatsResponse(BaseModel):
    """竞品统计响应"""
    ip_id: str
    competitor_count: int
    video_count: int
    avg_play_count: int


@router.get(
    "/strategy/v4/topics/recommend",
    response_model=TopicRecommendationV4Response,
    summary="获取选题推荐 V4.0（基于竞品爆款）",
    description="""
    基于竞品爆款的智能选题推荐。
    
    核心特点：
    - 抓取同类IP的近期爆款作为数据源
    - 内容重构引擎深度重构（非简单改写）
    - 已被竞品验证过的选题角度
    
    策略选项：
    - competitor_first: 优先竞品，不足时补充（默认）
    - competitor_only: 仅使用竞品数据
    - hybrid: 竞品+全网热点混合
    """
)
async def recommend_topics_v4(
    ip_id: str = Query(..., description="IP ID，如 xiaomin"),
    limit: int = Query(12, ge=1, le=30, description="推荐数量"),
    strategy: str = Query(
        "competitor_first", 
        description="推荐策略: competitor_first/competitor_only/hybrid"
    ),
    db: Session = Depends(get_db)
):
    """获取基于竞品爆款的选题推荐"""
    service = get_recommendation_service_v4()
    
    try:
        # 获取推荐
        topics = await service.recommend_topics(
            db=db,
            ip_id=ip_id,
            limit=limit,
            strategy=strategy
        )
        
        # 获取竞品统计
        stats = await service.get_competitor_stats(db, ip_id)
        
        # 转换为响应格式
        topic_list = []
        for topic in topics:
            topic_list.append({
                "id": topic.topic_id,
                "title": topic.title,
                "original_title": topic.original_title,
                "source": topic.source,
                "source_type": topic.source_type,
                "competitor_author": topic.competitor_author,
                "competitor_play_count": topic.competitor_play_count,
                "competitor_like_count": topic.competitor_like_count,
                "content_type": topic.content_type,
                "content_angle": topic.content_angle,
                "is_remixed": topic.is_remixed,
                "remix_confidence": topic.remix_confidence,
                "remix_reason": topic.remix_reason,
                "scores": topic.scores,
                "total_score": round(topic.total_score, 2),
                "tags": topic.tags,
                "url": topic.url,
            })
        
        return {
            "ip_id": ip_id,
            "total_count": len(topic_list),
            "strategy": strategy,
            "topics": topic_list,
            "competitor_stats": stats,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"推荐失败: {str(e)}"
        )


@router.get(
    "/strategy/v4/competitor-stats",
    response_model=CompetitorStatsResponse,
    summary="获取竞品统计数据"
)
async def get_competitor_stats(
    ip_id: str = Query(..., description="IP ID"),
    db: Session = Depends(get_db)
):
    """获取竞品账号的统计数据"""
    service = get_recommendation_service_v4()
    stats = await service.get_competitor_stats(db, ip_id)
    
    return {
        "ip_id": ip_id,
        "competitor_count": stats.get("competitor_count", 0),
        "video_count": stats.get("video_count", 0),
        "avg_play_count": stats.get("avg_play_count", 0),
    }


@router.post(
    "/strategy/v4/remix-test",
    summary="测试内容重构（调试用）"
)
async def test_remix(
    title: str = Query(..., description="原标题"),
    ip_id: str = Query(..., description="IP ID")
):
    """测试内容重构引擎"""
    from app.services.competitor_content_remixer import CompetitorContentRemixer
    
    remixer = CompetitorContentRemixer()
    
    # 模拟竞品选题
    test_topic = {
        "title": title,
        "extra": {
            "content_structure": {
                "hook_type": "数字",
                "conflict_point": "",
                "emotion_type": "励志",
                "target_audience": ""
            }
        }
    }
    
    # 模拟IP画像
    ip_profile = {
        "ip_id": ip_id,
        "expertise": "宝妈创业、副业变现",
        "target_audience": "宝妈、想赚钱的女性",
        "content_direction": "在家赚钱、女性成长"
    }
    
    result = remixer.remix(test_topic, ip_profile)
    
    if result:
        return {
            "original": result.original_title,
            "remixed": result.remixed_title,
            "confidence": result.confidence,
            "angle": result.angle.value,
            "content_type": result.structure.content_type,
            "reason": result.reason,
        }
    else:
        return {"error": "重构失败"}
