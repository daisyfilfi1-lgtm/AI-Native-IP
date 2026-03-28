"""
选题推荐路由 V2.0
基于IP的匹配爆款选题 API
"""

from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.topic_recommendation_v2 import (
    TopicRecommendationServiceV2,
    TopicRecommendation,
    get_service,
)

router = APIRouter(prefix="/strategy/v2", tags=["topic-recommendation-v2"])


# ═══════════════════════════════════════════════════════════
# 请求/响应模型
# ═══════════════════════════════════════════════════════════

class TopicRecommendResponse(BaseModel):
    """选题推荐响应"""
    id: str
    title: str
    original_title: str
    tags: List[str]
    score: float
    match_score: float
    content_type: str
    content_type_name: str
    source: str
    source_url: str
    reason: str
    estimated_views: str
    estimated_completion: int
    four_dim_score: dict


class TopicRecommendListResponse(BaseModel):
    """选题推荐列表响应"""
    topics: List[TopicRecommendResponse]
    total: int
    ip_id: str
    match_stats: dict = {}


class TopicMatchDetail(BaseModel):
    """匹配详情"""
    overall: float
    semantic: float
    keyword: float
    audience: float
    intent: float


# ═══════════════════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════════════════

@router.get("/topics/recommend", response_model=TopicRecommendListResponse)
async def recommend_topics_v2_api(
    ip_id: str = Query(..., description="IP ID"),
    limit: int = Query(12, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db),
):
    """
    智能选题推荐 V2.0 - 基于IP的匹配爆款选题
    
    核心改进：
    - 语义匹配代替严格关键词过滤
    - 内置爆款库兜底，确保始终返回高质量选题
    - 按4-3-2-1内容矩阵分配（40%搞钱/30%情感/20%技术/10%生活）
    - 详细的匹配度分析
    
    **示例响应**：
    ```json
    {
      "topics": [
        {
          "id": "builtin_money_0",
          "title": "2000块启动资金，我是如何做到月入3万的",
          "original_title": "2000块启动资金，我是如何做到月入3万的",
          "tags": ["低成本创业", "宝妈副业", "月入3万"],
          "score": 4.75,
          "match_score": 0.92,
          "content_type": "money",
          "content_type_name": "搞钱方法论",
          "source": "builtin",
          "source_url": "",
          "reason": "内置爆款库（搞钱方法论）- 匹配度92%",
          "estimated_views": "25万+",
          "estimated_completion": 80,
          "four_dim_score": {
            "total": 4.75,
            "relevance": 0.92,
            "hotness": 0.95,
            "competition": 0.52,
            "conversion": 0.90
          }
        }
      ],
      "total": 12,
      "ip_id": "xiaomin1",
      "match_stats": {
        "avg_match_score": 0.85,
        "content_type_distribution": {
          "money": 5,
          "emotion": 4,
          "skill": 2,
          "life": 1
        }
      }
    }
    ```
    """
    try:
        service = get_service()
        recommendations = await service.recommend_topics(db, ip_id, limit)
        
        # 转换响应格式
        topics = []
        for r in recommendations:
            topics.append(TopicRecommendResponse(
                id=r.id,
                title=r.title,
                original_title=r.original_title,
                tags=r.tags,
                score=r.score,
                match_score=r.match_score,
                content_type=r.content_type,
                content_type_name=r.content_type_name,
                source=r.source,
                source_url=r.source_url,
                reason=r.reason,
                estimated_views=r.estimated_views,
                estimated_completion=r.estimated_completion,
                four_dim_score=r.four_dim_score,
            ))
        
        # 统计信息
        match_scores = [t.match_score for t in recommendations]
        content_types = {}
        for t in recommendations:
            content_types[t.content_type] = content_types.get(t.content_type, 0) + 1
        
        return TopicRecommendListResponse(
            topics=topics,
            total=len(topics),
            ip_id=ip_id,
            match_stats={
                "avg_match_score": round(sum(match_scores) / len(match_scores), 2) if match_scores else 0,
                "content_type_distribution": content_types,
            }
        )
    
    except Exception as e:
        # 记录错误但不暴露内部信息
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Topic recommendation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="推荐服务暂时不可用，请稍后重试")


@router.get("/topics/builtin", response_model=TopicRecommendListResponse)
async def get_builtin_topics_api(
    ip_id: str = Query("xiaomin1", description="IP ID"),
    content_type: str = Query(None, description="内容类型筛选: money/emotion/skill/life"),
    limit: int = Query(12, ge=1, le=50, description="返回数量"),
):
    """
    获取内置爆款选题库
    
    用于：
    - 快速测试（无需配置TIKHUB）
    - TIKHUB失效时的兜底
    - 查看该IP的高质量选题模板
    """
    from app.services.builtin_topic_repository import get_builtin_topics, get_topics_by_matrix
    
    if content_type:
        topics_raw = get_builtin_topics(ip_id, content_type, limit)
    else:
        topics_raw = get_topics_by_matrix(ip_id, limit)
    
    topics = []
    for t in topics_raw:
        topics.append(TopicRecommendResponse(
            id=t.get("id", ""),
            title=t.get("title", ""),
            original_title=t.get("title", ""),
            tags=t.get("tags", []),
            score=t.get("score", 4.0),
            match_score=0.9,  # 内置库默认高匹配
            content_type=t.get("content_type", "other"),
            content_type_name=t.get("content_type", "其他"),
            source="builtin",
            source_url="",
            reason=f"内置爆款库 - {t.get('reason', '')}",
            estimated_views=t.get("estimatedViews", ""),
            estimated_completion=t.get("estimatedCompletion", 0),
            four_dim_score={
                "total": t.get("score", 4.0),
                "relevance": 0.9,
                "hotness": 0.95,
                "competition": 0.5,
                "conversion": 0.85,
            },
        ))
    
    return TopicRecommendListResponse(
        topics=topics,
        total=len(topics),
        ip_id=ip_id,
    )


@router.get("/topics/match-test")
async def test_topic_matching(
    ip_id: str = Query(..., description="IP ID"),
    topic_title: str = Query(..., description="测试的话题标题"),
    db: Session = Depends(get_db),
):
    """
    测试话题匹配算法
    
    用于调试和优化匹配算法效果
    
    **示例**：
    ```
    GET /api/v1/strategy/v2/topics/match-test?ip_id=xiaomin1&topic_title=宝妈创业月入3万的方法
    ```
    """
    from app.services.enhanced_topic_matcher import get_matcher
    from app.services.topic_recommendation_v2 import TopicRecommendationServiceV2
    
    service = TopicRecommendationServiceV2()
    ip_profile = service._get_ip_profile(db, ip_id)
    
    if not ip_profile:
        raise HTTPException(status_code=404, detail=f"IP not found: {ip_id}")
    
    # 构造测试话题
    test_topic = {
        "title": topic_title,
        "tags": [],
        "score": 4.5,
    }
    
    # 计算匹配分数
    matcher = get_matcher()
    match_scores = matcher.compute_match_score(ip_profile, test_topic)
    content_type = test_topic.get("content_type", "other")
    
    return {
        "ip_id": ip_id,
        "ip_profile": {
            "name": ip_profile.get("name"),
            "expertise": ip_profile.get("expertise"),
            "content_direction": ip_profile.get("content_direction"),
            "target_audience": ip_profile.get("target_audience"),
        },
        "test_topic": topic_title,
        "match_scores": match_scores,
        "content_type": content_type,
        "content_type_name": content_type,  # 简化处理
        "is_match": match_scores["overall"] >= 0.5,
    }


# ═══════════════════════════════════════════════════════════
# 兼容旧版API的路由
# ═══════════════════════════════════════════════════════════

@router.get("/topics/recommend-compat")
async def recommend_topics_compat(
    ip_id: str = Query(..., description="IP ID"),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    兼容旧版API格式的推荐接口
    
    返回格式与旧版 /strategy/topics/recommend 一致
    方便前端平滑迁移
    """
    try:
        service = get_service()
        recommendations = await service.recommend_topics(db, ip_id, limit)
        
        # 转换为旧版格式
        result = []
        for r in recommendations:
            result.append({
                "topic": r.title,
                "url": r.source_url,
                "platform": r.content_type_name,
                "traffic_score": r.four_dim_score.get("hotness", 0) * 100,
                "monetization_score": r.four_dim_score.get("conversion", 0) * 100,
                "fit_score": r.four_dim_score.get("relevance", 0) * 100,
                "cost_score": 70,  # 默认中等成本
                "overall_score": r.score,
                "total_score": int(r.score * 20),
                "viral_elements": r.tags[:3],
                "source": r.source,
            })
        
        return result
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Compat recommendation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="推荐服务暂时不可用")
