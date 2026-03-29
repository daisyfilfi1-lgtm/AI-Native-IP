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
                # V4 前端展示字段
                "competitor_name": topic.competitor_name,
                "competitor_platform": topic.competitor_platform,
                "remix_potential": topic.remix_potential,
                "viral_score": topic.viral_score,
                "original_plays": topic.original_plays,
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


@router.get(
    "/strategy/v4/competitor-videos",
    summary="获取按四维排序的竞品视频"
)
async def get_competitor_videos(
    ip_id: str = Query(..., description="IP ID"),
    limit: int = Query(12, ge=1, le=50, description="返回数量"),
    use_matrix: bool = Query(True, description="是否使用4-3-2-1内容矩阵"),
    db: Session = Depends(get_db)
):
    """
    获取按四维权重排序的竞品视频列表
    
    四维权重：
    - relevance (0.3): 与IP定位的相关度
    - hotness (0.3): 热度（点赞数等）
    - competition (0.2): 竞争度（越低越好）
    - conversion (0.2): 转化率潜力
    
    如果 use_matrix=true，按4-3-2-1矩阵分配：
    - 40% 搞钱 (money)
    - 30% 情感 (emotion)
    - 20% 技能 (skill)
    - 10% 生活 (life)
    """
    from app.services.competitor_sync_service import get_competitor_videos_by_four_dim
    
    videos = get_competitor_videos_by_four_dim(
        db_session=db,
        ip_id=ip_id,
        limit=limit,
        use_content_matrix=use_matrix
    )
    
    # 转换为前端友好的格式
    result = []
    for v in videos:
        result.append({
            "id": v["video_id"],
            "title": v["title"],
            "competitor_name": v["competitor_name"],
            "platform": v["platform"],
            "url": v["url"],
            "stats": {
                "likes": v["like_count"],
                "likes_display": v["hot_display"],
                "plays": v["play_count"],
                "comments": v["comment_count"],
                "shares": v["share_count"],
            },
            "content_type": v["content_type"],
            "tags": v["tags"],
            "four_dim": {
                "relevance": v["four_dim_relevance"],
                "hotness": v["four_dim_hotness"],
                "competition": v["four_dim_competition"],
                "conversion": v["four_dim_conversion"],
                "total": v["four_dim_total"],
                "weighted_score": round(v.get("weighted_score", 0), 2),
            },
            "fetched_at": v["fetched_at"].isoformat() if v["fetched_at"] else None,
        })
    
    return {
        "ip_id": ip_id,
        "total": len(result),
        "use_content_matrix": use_matrix,
        "videos": result,
    }


@router.post(
    "/strategy/v4/sync-competitors",
    summary="手动同步竞品数据（管理员用）"
)
async def sync_competitors(
    ip_id: str = Query(..., description="IP ID"),
    videos_per_competitor: int = Query(10, ge=1, le=20, description="每个竞品抓取视频数"),
    db: Session = Depends(get_db)
):
    """
    手动触发竞品数据同步
    
    从TIKHub抓取竞品视频并存储到数据库
    """
    from app.services.competitor_sync_service import CompetitorSyncService
    from scripts.sync_competitors_to_db import COMPETITORS
    
    service = CompetitorSyncService(db)
    
    results = await service.sync_all_competitors(
        ip_id=ip_id,
        competitors=COMPETITORS,
        videos_per_competitor=videos_per_competitor
    )
    
    total_synced = sum(r["synced"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    
    return {
        "ip_id": ip_id,
        "competitors_processed": len(results),
        "total_synced": total_synced,
        "total_errors": total_errors,
        "details": results,
    }


@router.get(
    "/strategy/v4/multi-source-test",
    summary="测试多源热榜（调试用）"
)
async def test_multi_source(
    ip_id: str = Query(..., description="IP ID"),
    limit: int = Query(12, ge=1, le=30, description="获取数量"),
    use_builtin_fallback: bool = Query(True, description="是否使用内置库兜底"),
    db: Session = Depends(get_db)
):
    """
    测试多源热榜聚合功能
    
    返回：
    - 各平台热榜数据
    - IP匹配度分析
    - 数据来源统计
    """
    from app.services.datasource.multi_source_hotlist import (
        get_multi_source_aggregator,
        fetch_hotlist_fallback,
    )
    from app.services.smart_ip_matcher import get_smart_matcher
    
    # 获取IP画像
    service = get_recommendation_service_v4()
    ip_profile = await service._get_ip_profile(db, ip_id)
    
    if not ip_profile:
        raise HTTPException(status_code=404, detail=f"IP不存在: {ip_id}")
    
    # 1. 获取多源热榜
    aggregator = get_multi_source_aggregator()
    multi_source_result = await aggregator.fetch_all(limit_per_platform=limit)
    
    # 2. 获取IP匹配的选题
    if use_builtin_fallback:
        best_topics = await fetch_hotlist_fallback(ip_profile, limit)
    else:
        best_result = await aggregator.fetch_best(ip_profile, limit)
        best_topics = aggregator.to_topic_data_list(best_result)
    
    # 3. 分析每条选题的IP匹配度
    matcher = get_smart_matcher()
    detailed_analysis = []
    
    for topic in best_topics[:10]:  # 只分析前10条
        match_result = matcher.analyze_match(topic.title, ip_profile)
        content_type, confidence = matcher.detect_content_type(topic.title)
        viral_elements = matcher.extract_viral_elements(topic.title)
        
        detailed_analysis.append({
            "title": topic.title,
            "source": topic.source,
            "platform": topic.platform,
            "match_score": match_result.overall,
            "match_dimensions": match_result.dimensions,
            "content_type": content_type,
            "content_type_confidence": confidence,
            "viral_elements": viral_elements,
            "match_reasons": match_result.reasons,
            "suggestions": match_result.suggestions,
        })
    
    return {
        "ip_id": ip_id,
        "ip_profile": {
            "name": ip_profile.get("name"),
            "expertise": ip_profile.get("expertise"),
            "target_audience": ip_profile.get("target_audience"),
        },
        "multi_source_stats": {
            "total_raw_items": len(multi_source_result.items),
            "source_breakdown": multi_source_result.source_stats,
            "fetch_time": multi_source_result.fetch_time.isoformat() if multi_source_result.fetch_time else None,
            "errors": multi_source_result.errors,
        },
        "recommended_topics": [
            {
                "id": t.id,
                "title": t.title,
                "source": t.source,
                "platform": t.platform,
                "tags": t.tags,
            }
            for t in best_topics
        ],
        "detailed_analysis": detailed_analysis,
        "using_builtin_fallback": use_builtin_fallback and len(multi_source_result.items) < limit // 2,
    }


@router.get(
    "/strategy/v4/builtin-topics",
    summary="获取内置爆款库选题（调试用）"
)
async def get_builtin_topics_api(
    ip_id: str = Query(..., description="IP ID"),
    limit: int = Query(12, ge=1, le=30, description="获取数量"),
    db: Session = Depends(get_db)
):
    """
    直接从内置爆款库获取选题
    
    用于测试内置库和IP类型检测
    """
    from app.services.datasource.builtin_viral_repository import get_builtin_repository
    from app.services.smart_ip_matcher import get_smart_matcher
    
    # 获取IP画像
    service = get_recommendation_service_v4()
    ip_profile = await service._get_ip_profile(db, ip_id)
    
    if not ip_profile:
        raise HTTPException(status_code=404, detail=f"IP不存在: {ip_id}")
    
    # 获取内置库选题
    repo = get_builtin_repository()
    topics = repo.get_topics_for_ip(ip_profile, limit)
    
    # 检测IP类型
    detected_types = repo.detect_ip_type(ip_profile)
    
    # 分析匹配度
    matcher = get_smart_matcher()
    analysis = []
    for topic in topics:
        match_score = matcher.calculate_match_score(topic.title, ip_profile)
        content_type, _ = matcher.detect_content_type(topic.title)
        analysis.append({
            "title": topic.title,
            "content_type": content_type,
            "match_score": match_score,
            "tags": topic.tags,
        })
    
    return {
        "ip_id": ip_id,
        "detected_ip_types": [t.value for t in detected_types],
        "ip_profile": {
            "expertise": ip_profile.get("expertise"),
            "content_direction": ip_profile.get("content_direction"),
            "target_audience": ip_profile.get("target_audience"),
        },
        "topics_count": len(topics),
        "topics": analysis,
    }
