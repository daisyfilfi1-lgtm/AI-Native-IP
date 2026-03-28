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

from app.services.datasource import get_datasource_manager_v2
from app.services.datasource.base import TopicData
from app.services.competitor_content_remixer import (
    CompetitorContentRemixer, 
    RemixResult,
    ContentAngle
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


class TopicRecommendationServiceV4:
    """
    选题推荐服务 V4.0
    
    核心策略：竞品驱动 + 内容重构
    """
    
    def __init__(self):
        self.datasource_manager = get_datasource_manager_v2()
        self.remixer = CompetitorContentRemixer()
        
        # 内容类型分布比例（4-3-2-1矩阵）
        self.content_matrix = {
            "money": 0.40,    # 40% 搞钱方法论
            "emotion": 0.30,  # 30% 情感共情
            "skill": 0.20,    # 20% 技术展示
            "life": 0.10,     # 10% 美好生活
        }
    
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
            topics = await self._fetch_competitor_topics(db, ip_profile, limit)
        elif strategy == "competitor_first":
            topics = await self._fetch_competitor_first(db, ip_profile, limit)
        else:  # hybrid
            topics = await self._fetch_hybrid(db, ip_profile, limit)
        
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
        limit: int
    ) -> List[TopicData]:
        """仅从竞品获取选题"""
        from app.services.datasource.competitor_source import CompetitorTopicDataSource
        
        source = CompetitorTopicDataSource(db_session=db)
        topics = await source.fetch(ip_profile, limit * 2)  # 多取一些用于筛选
        
        logger.info(f"[V4] Fetched {len(topics)} topics from competitors")
        return topics
    
    async def _fetch_competitor_first(
        self, 
        db, 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[TopicData]:
        """优先竞品，不足时补充其他来源"""
        # 先取竞品
        competitor_topics = await self._fetch_competitor_topics(db, ip_profile, int(limit * 0.8))
        
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
        limit: int
    ) -> List[TopicData]:
        """混合模式：竞品 + 全网热点"""
        # 竞品占60%
        competitor_limit = int(limit * 0.6)
        competitor_topics = await self._fetch_competitor_topics(db, ip_profile, competitor_limit)
        
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
        """从其他来源获取选题"""
        try:
            return await self.datasource_manager.fetch_with_strategy(
                ip_profile, limit, "smart"
            )
        except Exception as e:
            logger.warning(f"[V4] Failed to fetch from other sources: {e}")
            return []
    
    async def _fetch_hot_topics(
        self, 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[TopicData]:
        """从全网热点获取"""
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
            # 判断是否为竞品选题
            is_competitor = topic.extra.get("is_competitor_topic", False)
            needs_rewrite = topic.extra.get("needs_rewrite", False)
            
            if is_competitor and needs_rewrite:
                # 使用内容重构引擎
                remix_result = self.remixer.remix(
                    {
                        "title": topic.title,
                        "extra": topic.extra,
                    },
                    ip_profile
                )
                
                if remix_result and remix_result.confidence > 0.5:
                    # 重构成功
                    recommended = self._create_remixed_topic(topic, remix_result)
                    results.append(recommended)
                else:
                    # 重构失败，使用原标题
                    recommended = self._create_topic_from_data(topic)
                    results.append(recommended)
            else:
                # 非竞品选题，简单处理
                recommended = self._create_topic_from_data(topic)
                results.append(recommended)
        
        return results
    
    def _create_remixed_topic(
        self, 
        original: TopicData, 
        remix: RemixResult
    ) -> RecommendedTopicV4:
        """创建重构后的选题"""
        return RecommendedTopicV4(
            topic_id=original.id,
            title=remix.remixed_title,  # 使用重构后的标题
            original_title=remix.original_title,
            source=original.source,
            source_type="competitor",
            competitor_author=original.extra.get("competitor_author"),
            competitor_play_count=original.extra.get("play_count", 0),
            competitor_like_count=original.extra.get("like_count", 0),
            content_type=remix.structure.content_type,
            content_angle=remix.structure.angle.value,
            is_remixed=True,
            remix_confidence=remix.confidence,
            remix_reason=remix.reason,
            tags=original.tags,
            url=original.url,
            extra={
                "content_structure": remix.structure,
                **original.extra
            }
        )
    
    def _create_topic_from_data(self, topic: TopicData) -> RecommendedTopicV4:
        """从TopicData创建RecommendedTopicV4"""
        return RecommendedTopicV4(
            topic_id=topic.id,
            title=topic.title,
            original_title=topic.original_title,
            source=topic.source,
            source_type="other",
            content_type=topic.extra.get("content_type", "unknown"),
            tags=topic.tags,
            url=topic.url,
            extra=topic.extra
        )
    
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
        """计算IP适配度"""
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
            from sqlalchemy import text
            
            # 查询竞品账号数
            result = db.execute(
                text("SELECT COUNT(*) FROM competitor_accounts WHERE ip_id = :ip_id"),
                {"ip_id": ip_id}
            )
            competitor_count = result.scalar()
            
            # 查询竞品视频数
            result = db.execute(
                text("""
                    SELECT COUNT(*), AVG(play_count) 
                    FROM competitor_videos cv
                    JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
                    WHERE ca.ip_id = :ip_id
                """),
                {"ip_id": ip_id}
            )
            video_stats = result.fetchone()
            
            return {
                "competitor_count": competitor_count,
                "video_count": video_stats[0] if video_stats else 0,
                "avg_play_count": int(video_stats[1]) if video_stats and video_stats[1] else 0,
            }
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
