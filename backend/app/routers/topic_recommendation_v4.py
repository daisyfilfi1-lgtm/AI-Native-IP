"""
选题推荐API V4.0 - 基于竞品爆款的智能推荐

核心改进：
- 竞品爆款作为核心数据源
- 内容重构引擎（非模板改写）
- 已被同类IP验证过的选题
"""

from typing import Optional, List, Dict, Any
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


# ============== 环节2：爆款链接 → 提取标题/内容 ==============

class ExtractContentRequest(BaseModel):
    """内容提取请求"""
    url: str = Field(..., description="视频链接")
    use_cache: bool = Field(True, description="是否使用缓存")


class ExtractContentBatchRequest(BaseModel):
    """批量内容提取请求"""
    urls: List[str] = Field(..., description="视频链接列表", max_length=10)
    use_cache: bool = Field(True, description="是否使用缓存")


class ExtractedContentResponse(BaseModel):
    """提取内容响应 - 方案A：简化版（标题+标签）"""
    success: bool
    error: str = ""
    url: str
    platform: str
    video_id: str = ""
    author: str = ""
    
    # 核心内容
    original_title: str = ""      # 原始标题（含标签）
    title_clean: str = ""         # 纯净标题
    hook: str = ""                # 钩子（黄金3秒）
    body: str = ""                # 正文/角度
    tags: List[str] = []          # 话题标签
    
    # 分类
    content_type: str = ""        # money/emotion/skill/life
    
    # 数据
    stats: Dict[str, int] = {}    # 播放量/点赞数等
    
    # 提取信息
    extract_method: str = ""


@router.post(
    "/strategy/v4/extract-content",
    response_model=ExtractedContentResponse,
    summary="环节2：提取爆款链接内容（单条）"
)
async def extract_content_api(
    request: ExtractContentRequest
):
    """
    环节2核心API：从爆款链接提取结构化内容
    
    输入：抖音/小红书等平台视频链接
    输出：结构化内容（标题、钩子、正文、标签、爆款元素等）
    
    示例：
    ```json
    {
      "url": "https://www.douyin.com/video/xxxxx",
      "use_cache": true
    }
    ```
    
    返回：
    ```json
    {
      "success": true,
      "url": "https://www.douyin.com/video/xxxxx",
      "platform": "douyin",
      "video_id": "xxxxx",
      "author": "username",
      "original_title": "32岁，我终于活成了别人羡慕的样子#宝妈逆袭 #成长",
      "title_clean": "32岁，我终于活成了别人羡慕的样子",
      "hook": "32岁，我终于活成了别人羡慕的样子",
      "body": "",
      "tags": ["宝妈逆袭", "成长"],
      "content_type": "emotion",
      "stats": {
        "play_count": 150000,
        "like_count": 8500,
        "share_count": 1200
      },
      "extract_method": "tikhub_douyin"
    }
    ```
    """
    from app.services.smart_content_extractor import extract_content_for_remix, SmartContentExtractor
    from app.services.link_resolver import resolve_any_url, detect_platform
    
    # 首先尝试实时提取
    result = await extract_content_for_remix(request.url)
    
    # 如果实时提取失败，尝试从数据库查找
    if not result["success"]:
        try:
            # 解析URL获取video_id
            resolved = await resolve_any_url(request.url)
            resolved_url = resolved.get("resolved_url", request.url) if isinstance(resolved, dict) else resolved
            platform = detect_platform(resolved_url)
            
            # 从URL中提取video_id
            import re
            video_id = None
            if platform == "douyin":
                match = re.search(r'/video/(\d+)', resolved_url)
                if match:
                    video_id = match.group(1)
            
            if video_id:
                from app.db.session import SessionLocal
                from app.models.competitor_video import CompetitorVideo
                
                db = SessionLocal()
                try:
                    video = db.query(CompetitorVideo).filter(
                        CompetitorVideo.video_id == video_id
                    ).first()
                    
                    if video and video.original_title:
                        # 使用数据库数据构建结果
                        extractor = SmartContentExtractor()
                        result = {
                            "success": True,
                            "url": request.url,
                            "platform": platform or "unknown",
                            "video_id": video_id,
                            "author": video.author_name or "",
                            "original_title": video.original_title,
                            "title_clean": extractor._clean_title(video.original_title),
                            "hook": "",
                            "angle": "",
                            "tags": video.tags or [],
                            "content_type": video.content_type or "life",
                            "target_audience": "",
                            "viral_elements": [],
                            "stats": {
                                "play_count": video.play_count or 0,
                                "like_count": video.like_count or 0,
                                "share_count": 0
                            },
                            "rewrite_material": None,
                            "extract_method": "database_fallback"
                        }
                        
                        # 重新分析内容
                        hook, angle = extractor._split_title_structure(result["title_clean"])
                        result["hook"] = hook
                        result["angle"] = angle
                        result["target_audience"] = extractor._detect_audience(result["title_clean"], result["tags"])
                        result["viral_elements"] = extractor._analyze_viral_elements(result["title_clean"], result["tags"])
                        
                        # 构建改写素材
                        from app.services.smart_content_extractor import ContentAnalysis
                        analysis = ContentAnalysis(
                            original_title=video.original_title,
                            title_clean=result["title_clean"],
                            hook=hook,
                            angle=angle,
                            tags=result["tags"],
                            content_type=result["content_type"],
                            target_audience=result["target_audience"],
                            viral_elements=result["viral_elements"]
                        )
                        result["rewrite_material"] = analysis.to_rewrite_material()
                        
                finally:
                    db.close()
        except Exception as e:
            # 数据库回退也失败，保留原始错误
            pass
    
    return ExtractedContentResponse(
        success=result["success"],
        url=request.url,
        error=result.get("error", ""),
        **{k: v for k, v in result.items() if k not in ["success", "error", "original_text"]}
    )


@router.post(
    "/strategy/v4/extract-content/batch",
    summary="环节2：批量提取爆款链接内容"
)
async def extract_content_batch_api(
    request: ExtractContentBatchRequest
):
    """
    批量提取多个链接的内容
    
    适合从环节1获取多个链接后批量处理
    """
    from app.services.smart_content_extractor import extract_content_for_remix
    
    results = []
    
    # 并发提取（限制并发数）
    semaphore = asyncio.Semaphore(3)  # 最多3个并发
    
    async def extract_with_limit(url: str):
        async with semaphore:
            return await extract_content_for_remix(url)
    
    # 批量执行
    tasks = [extract_with_limit(url) for url in request.urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理结果
    processed = []
    for url, result in zip(request.urls, results):
        if isinstance(result, Exception):
            processed.append({
                "url": url,
                "success": False,
                "error": str(result)
            })
        else:
            processed.append(result)
    
    return {
        "total": len(request.urls),
        "successful": sum(1 for r in processed if r.get("success")),
        "failed": sum(1 for r in processed if not r.get("success")),
        "results": processed
    }


@router.get(
    "/strategy/v4/extract-content/test",
    summary="测试内容提取（GET方式，便于浏览器测试）"
)
async def extract_content_test(
    url: str = Query(..., description="视频链接")
):
    """
    测试用的GET接口，方便直接在浏览器测试
    
    示例：
    /strategy/v4/extract-content/test?url=https://www.douyin.com/video/xxxxx
    """
    from app.services.smart_content_extractor import extract_content_for_remix
    
    result = await extract_content_for_remix(url)
    
    return result


# ============== 完整流程：环节1 → 环节2 组合 ==============

@router.post(
    "/strategy/v4/competitor-full-pipeline",
    summary="完整流程：获取竞品 + 提取内容（环节1+2组合）"
)
async def competitor_full_pipeline(
    ip_id: str = Query(..., description="IP ID"),
    limit: int = Query(5, ge=1, le=10, description="获取数量"),
    extract_content: bool = Query(True, description="是否提取详细内容"),
    db: Session = Depends(get_db)
):
    """
    完整流程API：先获取竞品爆款，再提取详细内容
    
    一站式完成环节1+环节2
    """
    from app.services.competitor_sync_service import get_competitor_videos_by_four_dim
    from app.services.smart_content_extractor import extract_content_for_remix
    
    # 环节1：获取竞品视频（带链接）
    videos = get_competitor_videos_by_four_dim(
        db_session=db,
        ip_id=ip_id,
        limit=limit,
        use_content_matrix=True
    )
    
    if not extract_content:
        # 只返回链接，不提取内容
        return {
            "ip_id": ip_id,
            "stage": "1_only",
            "videos": videos
        }
    
    # 环节2：提取每个视频的内容
    results = []
    for video in videos:
        if video.get("url"):
            content = await extract_content_for_remix(video["url"])
            results.append({
                "video_info": video,
                "extracted_content": content
            })
    
    return {
        "ip_id": ip_id,
        "stage": "1_and_2",
        "total": len(results),
        "videos": results
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


# ============== 环节3：标题改写 ==============

class TitleRewriteRequest(BaseModel):
    """标题改写请求"""
    ip_id: str = Field(..., description="IP ID")
    original_title: str = Field(..., description="原始爆款标题")
    original_hook: str = Field(default="", description="原始hook（可选，为空则自动拆分）")
    original_body: str = Field(default="", description="原始body（可选）")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    content_type: str = Field(default="life", description="内容类型")
    strategy: str = Field(default="structure_keep", description="改写策略: structure_keep/emotion_shift/angle_flip")


class TitleRewriteResponse(BaseModel):
    """标题改写响应"""
    success: bool
    error: str = ""
    original: Dict[str, str] = {}
    rewritten: Dict[str, str] = {}
    strategy: str = ""
    ip_id: str = ""
    ip_name: str = ""
    content_type: str = ""


@router.post(
    "/strategy/v3/title-rewrite",
    response_model=TitleRewriteResponse,
    summary="环节3：爆款标题 + IP → 改写标题"
)
async def rewrite_title_api(
    request: TitleRewriteRequest
):
    """
    环节3核心API：基于爆款标题和IP人设生成改写标题
    
    输入：
    - ip_id: IP ID
    - original_title: 原始爆款标题
    - original_hook: 原始hook（可选）
    - original_body: 原始body（可选）
    - tags: 标签列表
    - content_type: 内容类型
    - strategy: 改写策略
    
    输出：
    - 改写后的标题（保留爆款结构，IP化内容）
    
    示例：
    ```json
    {
      "ip_id": "xiaomin",
      "original_title": "90后宝妈靠副业月入过万，分享3个真实方法",
      "original_hook": "90后宝妈靠副业月入过万",
      "original_body": "分享3个真实方法",
      "tags": ["宝妈副业", "赚钱技巧"],
      "content_type": "money",
      "strategy": "structure_keep"
    }
    ```
    
    返回：
    ```json
    {
      "success": true,
      "original": {
        "title": "90后宝妈靠副业月入过万，分享3个真实方法",
        "hook": "90后宝妈靠副业月入过万",
        "body": "分享3个真实方法"
      },
      "rewritten": {
        "title": "设计师靠AI副业月入3万，分享我的3个接单渠道",
        "hook": "设计师靠AI副业月入3万",
        "body": "分享我的3个接单渠道"
      },
      "strategy": "structure_keep",
      "ip_id": "xiaomin",
      "ip_name": "小敏设计师"
    }
    ```
    """
    from app.services.title_rewrite_service import rewrite_title
    
    # 如果没有提供hook/body，自动拆分
    hook = request.original_hook
    body = request.original_body
    
    if not hook and not body:
        from app.services.smart_content_extractor import SmartContentExtractor
        extractor = SmartContentExtractor()
        hook, body = extractor._split_title_structure(request.original_title)
    
    result = await rewrite_title(
        ip_id=request.ip_id,
        original_title=request.original_title,
        original_hook=hook,
        original_body=body,
        tags=request.tags,
        content_type=request.content_type,
        strategy=request.strategy
    )
    
    return TitleRewriteResponse(
        success=result["success"],
        error=result.get("error", ""),
        original=result.get("original", {}),
        rewritten=result.get("rewritten", {}),
        strategy=result.get("strategy", ""),
        ip_id=result.get("ip_id", ""),
        ip_name=result.get("ip_name", ""),
        content_type=result.get("content_type", "")
    )


class BatchRewriteRequest(BaseModel):
    """批量改写请求"""
    titles: List[Dict[str, Any]] = Field(..., description="标题列表")


@router.post(
    "/strategy/v3/title-rewrite/batch",
    summary="环节3：批量改写标题"
)
async def batch_rewrite_titles_api(
    request: BatchRewriteRequest,
    ip_id: str = Query(..., description="IP ID"),
    strategy: str = Query("structure_keep", description="改写策略")
):
    """
    批量改写多个标题
    
    适合从环节2获取多个爆款标题后批量改写
    """
    from app.services.title_rewrite_service import rewrite_title
    
    results = []
    
    for item in request.titles:
        result = await rewrite_title(
            ip_id=ip_id,
            original_title=item.get("title", ""),
            original_hook=item.get("hook", ""),
            original_body=item.get("body", ""),
            tags=item.get("tags", []),
            content_type=item.get("content_type", "life"),
            strategy=strategy
        )
        results.append(result)
    
    return {
        "ip_id": ip_id,
        "strategy": strategy,
        "total": len(results),
        "success_count": sum(1 for r in results if r["success"]),
        "results": results
    }


@router.post(
    "/strategy/v3/full-pipeline",
    summary="完整流程：URL → 提取 → 改写（环节2+3组合）"
)
async def full_pipeline_api(
    ip_id: str = Query(..., description="IP ID"),
    url: str = Query(..., description="视频链接"),
    rewrite_strategy: str = Query("structure_keep", description="改写策略")
):
    """
    完整流程API：一站式完成环节2（提取）+ 环节3（改写）
    
    输入视频链接，直接返回改写后的标题
    """
    from app.services.smart_content_extractor import extract_content_for_remix
    from app.services.title_rewrite_service import rewrite_title
    
    # 环节2：提取内容
    extracted = await extract_content_for_remix(url)
    
    if not extracted.get("success"):
        return {
            "success": False,
            "error": extracted.get("error", "提取失败"),
            "stage": "extraction_failed"
        }
    
    # 环节3：改写标题
    rewrite_result = await rewrite_title(
        ip_id=ip_id,
        original_title=extracted.get("original_title", ""),
        original_hook=extracted.get("hook", ""),
        original_body=extracted.get("body", ""),
        tags=extracted.get("tags", []),
        content_type=extracted.get("content_type", "life"),
        strategy=rewrite_strategy
    )
    
    return {
        "success": True,
        "stage": "extraction_and_rewrite",
        "ip_id": ip_id,
        "source_url": url,
        "extracted": {
            "title": extracted.get("original_title"),
            "hook": extracted.get("hook"),
            "body": extracted.get("body"),
            "tags": extracted.get("tags"),
            "content_type": extracted.get("content_type"),
            "stats": extracted.get("stats")
        },
        "rewritten": rewrite_result.get("rewritten", {}),
        "strategy": rewrite_strategy
    }


# ============== 环节4：内容生成 ==============

class ContentGenerationRequest(BaseModel):
    """内容生成请求"""
    ip_id: str = Field(..., description="IP ID")
    title: str = Field(..., description="改写后的标题")
    hook: str = Field(default="", description="hook部分")
    body: str = Field(default="", description="body部分")
    content_type: str = Field(default="life", description="内容类型")
    target_duration: int = Field(default=60, description="目标时长（秒）")
    use_rag: bool = Field(default=True, description="是否使用向量检索素材")


class ContentGenerationResponse(BaseModel):
    """内容生成响应"""
    success: bool
    error: str = ""
    ip_id: str = ""
    ip_name: str = ""
    title: str = ""
    script: str = ""  # 完整口播稿
    sections: Dict[str, str] = {}  # 分段内容
    reference_assets: List[Dict] = []
    word_count: int = 0
    estimated_duration: int = 0


@router.post(
    "/strategy/v4/content-generate",
    response_model=ContentGenerationResponse,
    summary="环节4：改写标题 + IP素材 → 内容生成"
)
async def generate_content_api(
    request: ContentGenerationRequest
):
    """
    环节4核心API：基于改写后的标题和IP素材生成视频口播稿
    
    输入：
    - ip_id: IP ID
    - title: 改写后的完整标题
    - hook: hook部分
    - body: body部分
    - content_type: 内容类型
    - target_duration: 目标时长（秒）
    - use_rag: 是否使用向量检索素材
    
    输出：
    - 完整口播稿（黄金3秒+正文+结尾）
    - 使用的参考素材
    - 字数和预估时长
    
    示例：
    ```json
    {
      "ip_id": "xiaomin",
      "title": "UI设计师靠AI接私单月入3万，分享我的3个获客渠道",
      "hook": "UI设计师靠AI接私单月入3万",
      "body": "分享我的3个获客渠道",
      "content_type": "money",
      "target_duration": 60
    }
    ```
    
    返回：
    ```json
    {
      "success": true,
      "ip_id": "xiaomin",
      "ip_name": "小敏",
      "title": "UI设计师靠AI接私单月入3万，分享我的3个获客渠道",
      "script": "（完整口播稿内容）",
      "sections": {
        "hook": "黄金3秒内容",
        "body": "正文内容",
        "cta": "结尾引导"
      },
      "reference_assets": [
        {"title": "素材1", "type": "article"}
      ],
      "word_count": 240,
      "estimated_duration": 60
    }
    ```
    """
    from app.services.content_generation_service import generate_content
    
    result = await generate_content(
        ip_id=request.ip_id,
        title=request.title,
        hook=request.hook,
        body=request.body,
        content_type=request.content_type,
        target_duration=request.target_duration,
        use_rag=request.use_rag
    )
    
    return ContentGenerationResponse(
        success=result["success"],
        error=result.get("error", ""),
        ip_id=result.get("ip_id", ""),
        ip_name=result.get("ip_name", ""),
        title=result.get("title", ""),
        script=result.get("script", ""),
        sections=result.get("sections", {}),
        reference_assets=result.get("reference_assets", []),
        word_count=result.get("word_count", 0),
        estimated_duration=result.get("estimated_duration", 0)
    )


@router.post(
    "/strategy/v4/complete-pipeline",
    summary="完整流程：URL → 提取 → 改写 → 生成（环节2+3+4组合）"
)
async def complete_pipeline_api(
    ip_id: str = Query(..., description="IP ID"),
    url: str = Query(..., description="视频链接"),
    rewrite_strategy: str = Query("structure_keep", description="改写策略"),
    target_duration: int = Query(60, description="目标视频时长（秒）")
):
    """
    完整流程API：一站式完成环节2（提取）+ 环节3（改写）+ 环节4（生成）
    
    输入视频链接，直接返回完整的视频口播稿
    """
    from app.services.smart_content_extractor import extract_content_for_remix
    from app.services.title_rewrite_service import rewrite_title
    from app.services.content_generation_service import generate_content
    
    # 环节2：提取内容
    extracted = await extract_content_for_remix(url)
    
    if not extracted.get("success"):
        return {
            "success": False,
            "error": extracted.get("error", "提取失败"),
            "stage": "extraction_failed"
        }
    
    # 环节3：改写标题
    rewrite_result = await rewrite_title(
        ip_id=ip_id,
        original_title=extracted.get("original_title", ""),
        original_hook=extracted.get("hook", ""),
        original_body=extracted.get("body", ""),
        tags=extracted.get("tags", []),
        content_type=extracted.get("content_type", "life"),
        strategy=rewrite_strategy
    )
    
    if not rewrite_result.get("success"):
        return {
            "success": False,
            "error": rewrite_result.get("error", "改写失败"),
            "stage": "rewrite_failed",
            "extracted": extracted
        }
    
    # 环节4：生成内容
    rewritten = rewrite_result.get("rewritten", {})
    generated = await generate_content(
        ip_id=ip_id,
        title=rewritten.get("title", ""),
        hook=rewritten.get("hook", ""),
        body=rewritten.get("body", ""),
        content_type=extracted.get("content_type", "life"),
        target_duration=target_duration
    )
    
    return {
        "success": True,
        "stage": "complete",
        "ip_id": ip_id,
        "source_url": url,
        "pipeline": {
            "stage2_extraction": {
                "title": extracted.get("original_title"),
                "hook": extracted.get("hook"),
                "body": extracted.get("body"),
                "tags": extracted.get("tags"),
                "content_type": extracted.get("content_type")
            },
            "stage3_rewrite": {
                "original": rewrite_result.get("original"),
                "rewritten": rewritten,
                "strategy": rewrite_result.get("strategy"),
                "analysis": rewrite_result.get("analysis")
            },
            "stage4_generation": {
                "script": generated.get("script"),
                "sections": generated.get("sections"),
                "word_count": generated.get("word_count"),
                "estimated_duration": generated.get("estimated_duration"),
                "reference_assets": generated.get("reference_assets")
            }
        }
    }
