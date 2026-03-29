"""
选题推荐服务 V4.0 - 基于竞品爆款的智能推荐

核心改进：
1. 竞品爆款作为核心数据源(P0)
2. 内容重构引擎替代简单改写
3. 爆款验证机制（已被同类IP验证过）

推荐流程：
竞品账号 → 抓取爆款 → 内容结构分析 → IP视角重构 → 质量评估 → 4-3-2-1分布
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote

from app.services.datasource import get_datasource_manager_v2
from app.services.datasource.base import TopicData
from app.services.datasource.multi_source_hotlist import (
    fetch_multi_source_hotlist,
    fetch_hotlist_fallback,
    get_multi_source_aggregator,
)
from app.services.datasource.builtin_viral_repository import (
    get_builtin_repository,
    BuiltinViralRepository,
)
from app.services.smart_ip_matcher import get_smart_matcher
from app.services.real_competitor_service import (
    fetch_competitor_viral_topics,
    get_real_competitor_service,
)
logger = logging.getLogger(__name__)


@dataclass
class RecommendedTopicV4:
    """推荐选题V4数据结构"""
    topic_id: str
    title: str
    original_title: str
    
    # 来源信息
    source: str
    source_type: str  # competitor / hot / builtin
    competitor_author: Optional[str] = None
    
    # 数据表现（竞品验证）
    competitor_play_count: int = 0
    competitor_like_count: int = 0
    
    # 内容分析
    content_type: str = ""  # money/emotion/skill/life
    content_angle: str = ""  # 内容角度
    
    # 重构信息
    is_remixed: bool = False
    remix_confidence: float = 0.0
    remix_reason: str = ""
    
    # 评分
    scores: Dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    
    # 元数据
    tags: List[str] = field(default_factory=list)
    url: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    
    # V4 前端展示字段
    competitor_name: Optional[str] = None  # 竞品账号名称
    competitor_platform: Optional[str] = None  # 竞品平台
    remix_potential: Optional[str] = None  # high/medium/low
    viral_score: Optional[int] = None  # 爆款分数 0-100
    original_plays: Optional[str] = None  # 原视频播放量显示


class TopicRecommendationServiceV4:
    """
    选题推荐服务 V4.0
    
    核心策略：竞品驱动 + 内容重构
    """
    
    def __init__(self):
        self.datasource_manager = get_datasource_manager_v2()
        # 内容类型分布比例（4-3-2-1矩阵）
        self.content_matrix = {
            "money": 0.40,  # 40% 搞钱方法论
            "emotion": 0.30,  # 30% 情感共情
            "skill": 0.20,  # 20% 技术展示
            "life": 0.10,  # 10% 美好生活
        }

    @staticmethod
    def _fallback_topic_url(title: str, platform: str = "douyin") -> str:
        """大数据源未给链接时，用原标题生成可打开的搜索页（与 TikHub billboard 逻辑一致）。"""
        t = (title or "").strip()
        if not t:
            return ""
        q = t[:80].replace(" ", "").replace("?", "").replace("？", "")
        if not q:
            return ""
        safe_q = quote(q, safe="")
        plat = (platform or "douyin").lower()
        if plat == "xiaohongshu":
            return f"https://www.xiaohongshu.com/search_result?keyword={safe_q}"
        return f"https://www.douyin.com/search/{safe_q}"

    async def recommend_topics(
        self, 
        db,
        ip_id: str,
        limit: int = 12,
        strategy: str = "competitor_first"
    ) -> List[RecommendedTopicV4]:
        """
        推荐选题 - V4主入口
        
        Args:
            db: 数据库会话
            ip_id: IP ID
            limit: 推荐数量
            strategy: 推荐策略
                - competitor_first: 优先竞品（默认）
                - competitor_only: 仅竞品
                - hybrid: 混合模式
        """
        # 1. 获取IP画像
        ip_profile = await self._get_ip_profile(db, ip_id)
        if not ip_profile:
            logger.error(f"[V4] IP not found: {ip_id}")
            return []
        
        logger.info(f"[V4] Recommending topics for IP: {ip_id}, strategy: {strategy}")
        
        # 2. 根据策略获取选题
        if strategy == "competitor_only":
            topics = await self._fetch_competitor_topics(db, ip_profile, limit, ip_id)
        elif strategy == "competitor_first":
            topics = await self._fetch_competitor_first(db, ip_profile, limit, ip_id)
        else:  # hybrid
            topics = await self._fetch_hybrid(db, ip_profile, limit, ip_id)
        
        # 3. 内容重构（针对竞品选题）
        remixed_topics = await self._remix_topics(topics, ip_profile)
        
        # 4. 质量评估和排序
        scored_topics = self._score_topics(remixed_topics, ip_profile)
        
        # 5. 按内容矩阵分布
        distributed = self._distribute_by_matrix(scored_topics, limit)
        
        logger.info(f"[V4] Returning {len(distributed)} topics for IP: {ip_id}")
        return distributed
    
    async def _get_ip_profile(self, db, ip_id: str) -> Optional[Dict[str, Any]]:
        """获取IP画像"""
        try:
            from sqlalchemy import text
            result = db.execute(
                text("SELECT * FROM ip WHERE ip_id = :ip_id"),
                {"ip_id": ip_id}
            )
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
        except Exception as e:
            logger.error(f"[V4] Failed to get IP profile: {e}")
            return None
    
    async def _fetch_competitor_topics(
        self, 
        db, 
        ip_profile: Dict[str, Any], 
        limit: int,
        ip_id: str = None
    ) -> List[TopicData]:
        """
        从竞品获取选题
        
        【推荐方案】使用Railway数据库中已有的竞品数据
        - competitor_accounts: 竞品账号配置
        - competitor_videos: 竞品视频数据
        
        优势：
        1. 数据已同步，无需实时抓取API
        2. 竞品与IP同领域，匹配度高
        3. 有真实播放量验证
        """
        if not ip_id:
            logger.warning("[V4] No ip_id provided, cannot fetch competitor topics")
            return []
        
        try:
            logger.info(f"[V4] Fetching viral topics from database (competitor_videos)...")
            
            # 使用真实竞品服务（从数据库读取）
            service = get_real_competitor_service(db)
            result = await service.fetch_viral_topics(
                ip_id=ip_id,
                ip_profile=ip_profile,
                limit=limit,
                min_play_count=10000,  # 至少1万播放才算爆款
                days_back=30
            )
            
            if result.topics:
                logger.info(
                    f"[V4] Got {len(result.topics)} topics from "
                    f"{result.stats.get('competitor_count', 0)} competitors "
                    f"(DB: {result.from_db})"
                )
                return result.topics
            
            # 如果数据库没有数据，降级到内置库
            logger.warning(
                f"[V4] No competitor videos in database for IP: {ip_id}, "
                f"using builtin fallback"
            )
            return []
            
        except Exception as e:
            logger.error(f"[V4] Failed to fetch competitor topics: {e}")
            return []
    
    async def _fetch_competitor_first(
        self, 
        db, 
        ip_profile: Dict[str, Any], 
        limit: int,
        ip_id: str = None
    ) -> List[TopicData]:
        """优先竞品，不足时补充其他来源"""
        # 先取竞品
        competitor_topics = await self._fetch_competitor_topics(db, ip_profile, int(limit * 0.8), ip_id)
        
        # 如果竞品不足，补充其他来源
        if len(competitor_topics) < limit:
            remaining = limit - len(competitor_topics)
            other_topics = await self._fetch_other_sources(ip_profile, remaining)
            competitor_topics.extend(other_topics)
        
        return competitor_topics
    
    async def _fetch_hybrid(
        self, 
        db, 
        ip_profile: Dict[str, Any], 
        limit: int,
        ip_id: str = None
    ) -> List[TopicData]:
        """混合模式：竞品 + 全网热点"""
        # 竞品占60%
        competitor_limit = int(limit * 0.6)
        competitor_topics = await self._fetch_competitor_topics(db, ip_profile, competitor_limit, ip_id)
        
        # 全网热点占40%
        hot_limit = limit - len(competitor_topics)
        hot_topics = await self._fetch_hot_topics(ip_profile, hot_limit)
        
        competitor_topics.extend(hot_topics)
        return competitor_topics
    
    async def _fetch_other_sources(
        self, 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[TopicData]:
        """
        从其他来源获取选题
        
        新策略：
        1. 优先使用多源热榜聚合（抖音+小红书+快手+B站）
        2. 如果都失败，使用内置爆款库兜底
        """
        try:
            # 1. 尝试多源热榜聚合
            logger.info(f"[V4] Fetching from multi-source hotlist...")
            multi_source_topics = await fetch_hotlist_fallback(ip_profile, limit)
            
            if multi_source_topics and len(multi_source_topics) >= limit // 2:
                logger.info(f"[V4] Got {len(multi_source_topics)} topics from multi-source")
                return multi_source_topics
            
            # 2. 多源不足，使用内置库兜底
            logger.warning(f"[V4] Multi-source insufficient, using builtin fallback")
            builtin_repo = get_builtin_repository()
            builtin_topics = builtin_repo.get_topics_for_ip(ip_profile, limit)
            
            # 3. 合并结果
            if multi_source_topics:
                # 去重合并
                seen_titles = {t.title for t in multi_source_topics}
                for topic in builtin_topics:
                    if topic.title not in seen_titles:
                        multi_source_topics.append(topic)
                return multi_source_topics[:limit]
            
            return builtin_topics
            
        except Exception as e:
            logger.error(f"[V4] Failed to fetch from other sources: {e}")
            # 最终兜底：返回内置库
            try:
                builtin_repo = get_builtin_repository()
                return builtin_repo.get_topics_for_ip(ip_profile, limit)
            except Exception as e2:
                logger.error(f"[V4] Builtin fallback also failed: {e2}")
                return []
    
    async def _fetch_hot_topics(
        self, 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[TopicData]:
        """
        从全网热点获取
        
        使用多源热榜聚合
        """
        return await self._fetch_other_sources(ip_profile, limit)
    
    async def _remix_topics(
        self, 
        topics: List[TopicData], 
        ip_profile: Dict[str, Any]
    ) -> List[RecommendedTopicV4]:
        """
        对选题进行内容重构
        
        竞品选题 → 内容重构
        其他选题 → 简单改写（保持兼容）
        """
        results = []
        
        for topic in topics:
            # 非竞品选题与竞品选题统一走简单处理
            # 深度仿写由用户进入仿写流程后通过 enhanced_remix_pipeline 完成
            recommended = self._create_topic_from_data(topic)
            results.append(recommended)
        
        return results
    
    
    def _create_topic_from_data(self, topic: TopicData) -> RecommendedTopicV4:
        """从TopicData创建RecommendedTopicV4"""
        play_count = int(topic.extra.get("play_count") or 0)
        like_count = int(topic.extra.get("like_count") or 0)
        is_competitor = topic.extra.get("is_competitor_topic", False)
        # 非竞品热点（抖音热榜等）也展示播放量与爆款分，便于与大数据对齐
        resolved_url = (topic.url or "").strip() or self._fallback_topic_url(
            topic.original_title or topic.title,
            topic.platform,
        )

        return RecommendedTopicV4(
            topic_id=topic.id,
            title=topic.title,
            original_title=topic.original_title,
            source=topic.source,
            source_type="competitor" if is_competitor else "other",
            competitor_author=topic.extra.get("competitor_author"),
            competitor_play_count=play_count,
            competitor_like_count=like_count,
            content_type=topic.extra.get("content_type", "unknown"),
            tags=topic.tags,
            url=resolved_url,
            extra=topic.extra,
            # V4 前端展示字段（如果是竞品选题）
            competitor_name=topic.extra.get("competitor_name") if is_competitor else None,
            competitor_platform=topic.extra.get("competitor_platform", "douyin") if is_competitor else None,
            remix_potential=self._calculate_remix_potential(play_count, 0.5) if is_competitor else None,
            viral_score=self._calculate_viral_score(play_count, like_count)
            if (play_count > 0 or like_count > 0)
            else None,
            original_plays=self._format_play_count(play_count) if play_count > 0 else None,
        )
    
    def _calculate_remix_potential(self, play_count: int, confidence: float) -> str:
        """计算仿写潜力"""
        if play_count > 100000 and confidence > 0.7:
            return "high"
        elif play_count > 50000 and confidence > 0.5:
            return "medium"
        else:
            return "low"
    
    def _calculate_viral_score(self, play_count: int, like_count: int) -> int:
        """计算爆款分数 0-100"""
        score = 0
        
        # 播放量分数 (最高60分)
        if play_count > 500000:
            score += 60
        elif play_count > 100000:
            score += 50
        elif play_count > 50000:
            score += 40
        elif play_count > 10000:
            score += 30
        elif play_count > 5000:
            score += 20
        else:
            score += 10
        
        # 互动率分数 (最高40分)
        if play_count > 0:
            engagement_rate = like_count / play_count
            if engagement_rate > 0.1:
                score += 40
            elif engagement_rate > 0.05:
                score += 30
            elif engagement_rate > 0.02:
                score += 20
            else:
                score += 10
        
        return min(100, score)
    
    def _format_play_count(self, play_count: int) -> str:
        """格式化播放量显示"""
        if play_count >= 1000000:
            return f"{play_count / 10000:.0f}万+"
        elif play_count >= 10000:
            return f"{play_count / 10000:.1f}万"
        elif play_count >= 1000:
            return f"{play_count / 1000:.1f}千"
        else:
            return str(play_count)
    
    def _score_topics(
        self, 
        topics: List[RecommendedTopicV4], 
        ip_profile: Dict[str, Any]
    ) -> List[RecommendedTopicV4]:
        """对选题进行综合评分"""
        for topic in topics:
            scores = {}
            
            # 1. 竞品验证分（已被验证过的选题）
            if topic.competitor_play_count > 0:
                if topic.competitor_play_count > 100000:
                    scores["verified"] = 1.0
                elif topic.competitor_play_count > 50000:
                    scores["verified"] = 0.8
                elif topic.competitor_play_count > 10000:
                    scores["verified"] = 0.6
                else:
                    scores["verified"] = 0.4
            else:
                scores["verified"] = 0.3
            
            # 2. 重构质量分
            if topic.is_remixed:
                scores["remix_quality"] = topic.remix_confidence
            else:
                scores["remix_quality"] = 0.5
            
            # 3. 时效分
            scores["freshness"] = 0.8  # 竞品数据通常较新
            
            # 4. IP适配分
            scores["ip_fit"] = self._calculate_ip_fit(topic, ip_profile)
            
            # 计算总分（加权平均）
            weights = {
                "verified": 0.35,
                "remix_quality": 0.25,
                "freshness": 0.20,
                "ip_fit": 0.20,
            }
            
            topic.scores = scores
            topic.total_score = sum(scores[k] * weights[k] for k in weights)
        
        # 按总分排序
        topics.sort(key=lambda x: x.total_score, reverse=True)
        return topics
    
    def _calculate_ip_fit(
        self, 
        topic: RecommendedTopicV4, 
        ip_profile: Dict[str, Any]
    ) -> float:
        """
        计算IP适配度
        
        使用智能匹配器进行语义级匹配
        """
        try:
            matcher = get_smart_matcher()
            match_result = matcher.analyze_match(topic.title, ip_profile)
            return match_result.overall
        except Exception as e:
            logger.warning(f"[V4] Smart matcher failed, using fallback: {e}")
            # 降级到简单匹配
            fit_score = 0.5
            
            # 内容类型匹配
            ip_expertise = ip_profile.get("expertise", "")
            if topic.content_type == "money" and "创业" in ip_expertise:
                fit_score += 0.3
            elif topic.content_type == "emotion" and "情感" in ip_expertise:
                fit_score += 0.3
            
            # 标签匹配
            ip_tags = set(ip_profile.get("target_audience", "").split(","))
            topic_tags = set(topic.tags)
            overlap = ip_tags & topic_tags
            if overlap:
                fit_score += min(0.2, len(overlap) * 0.1)
            
            return min(1.0, fit_score)
    
    def _distribute_by_matrix(
        self, 
        topics: List[RecommendedTopicV4], 
        limit: int
    ) -> List[RecommendedTopicV4]:
        """按4-3-2-1内容矩阵分布选题"""
        # 按内容类型分组
        by_type = {"money": [], "emotion": [], "skill": [], "life": []}
        for topic in topics:
            t = topic.content_type if topic.content_type in by_type else "life"
            by_type[t].append(topic)
        
        # 计算各类型配额
        result = []
        quotas = {
            "money": int(limit * self.content_matrix["money"]),
            "emotion": int(limit * self.content_matrix["emotion"]),
            "skill": int(limit * self.content_matrix["skill"]),
            "life": limit - int(limit * 0.9),  # 剩余给life
        }
        
        # 按配额选取
        for content_type, quota in quotas.items():
            selected = by_type[content_type][:quota]
            result.extend(selected)
        
        # 如果不够，从高分选题补充
        if len(result) < limit:
            existing_ids = {t.topic_id for t in result}
            for topic in topics:
                if topic.topic_id not in existing_ids:
                    result.append(topic)
                    if len(result) >= limit:
                        break
        
        return result[:limit]
    
    async def get_competitor_stats(
        self, 
        db, 
        ip_id: str
    ) -> Dict[str, Any]:
        """获取竞品统计数据"""
        try:
            service = get_real_competitor_service(db)
            return await service.get_competitor_stats(ip_id)
        except Exception as e:
            logger.error(f"[V4] Failed to get competitor stats: {e}")
            return {}


# 全局实例
_v4_service: Optional[TopicRecommendationServiceV4] = None


def get_recommendation_service_v4() -> TopicRecommendationServiceV4:
    """获取V4推荐服务实例"""
    global _v4_service
    if _v4_service is None:
        _v4_service = TopicRecommendationServiceV4()
    return _v4_service
