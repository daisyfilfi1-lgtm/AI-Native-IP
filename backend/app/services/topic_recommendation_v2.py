"""
智能选题推荐服务 V2.0
基于IP的匹配爆款选题
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP
from app.services.strategy_config_service import get_merged_config
from app.services.builtin_topic_repository import (
    get_builtin_topics,
    get_topics_by_matrix,
    get_emergency_topics,
)
from app.services.enhanced_topic_matcher import (
    EnhancedTopicMatcher,
    get_matcher,
)
from app.services.keyword_synonyms import classify_content_type, get_content_type_name
from app.services import tikhub_client, douyin_hot_hub_client

logger = logging.getLogger(__name__)


@dataclass
class TopicRecommendation:
    """选题推荐结果"""
    id: str
    title: str
    original_title: str
    tags: List[str]
    score: float  # 0-5分
    match_score: float  # IP匹配度
    four_dim_score: Dict[str, float]
    content_type: str  # money/emotion/skill/life
    content_type_name: str
    source: str  # tikhub/builtin/algorithm
    source_url: str
    reason: str
    estimated_views: str
    estimated_completion: int


class TopicRecommendationServiceV2:
    """
    选题推荐服务 V2.0
    
    核心改进：
    1. 优先使用内置爆款库（高质量、可控）
    2. 语义匹配代替严格关键词过滤
    3. 多数据源融合（TIKHUB + 内置库）
    4. 按4-3-2-1内容矩阵分配
    """
    
    def __init__(self):
        self.matcher = EnhancedTopicMatcher()
    
    async def recommend_topics(
        self,
        db: Session,
        ip_id: str,
        limit: int = 12,
        use_builtin_fallback: bool = True,
    ) -> List[TopicRecommendation]:
        """
        推荐选题主入口
        
        Args:
            db: 数据库会话
            ip_id: IP ID
            limit: 返回数量
            use_builtin_fallback: 是否使用内置库兜底
            
        Returns:
            推荐的选题列表
        """
        # 1. 获取IP画像
        ip_profile = self._get_ip_profile(db, ip_id)
        if not ip_profile:
            logger.warning(f"IP not found: {ip_id}, using generic topics")
            return self._get_generic_recommendations(ip_id, limit)
        
        # 2. 获取策略配置
        strategy = get_merged_config(db, ip_id)
        weights = strategy.get("four_dim_weights", {
            "relevance": 0.3, "hotness": 0.3, "competition": 0.2, "conversion": 0.2
        })
        
        # 3. 并行获取多源数据
        all_topics = await self._fetch_all_sources(ip_id, ip_profile, limit * 2)
        
        # 4. 如果外部数据源返回为空，直接使用内置库
        if not all_topics and use_builtin_fallback:
            logger.info(f"No external data for {ip_id}, using builtin topics")
            return self._get_builtin_recommendations(ip_id, limit, weights)
        
        # 5. 语义匹配和评分
        matched_topics = self.matcher.filter_and_rank_topics(
            ip_profile, all_topics, threshold=0.25, top_k=limit * 2
        )
        
        # 6. 如果匹配结果不足，补充内置库
        if len(matched_topics) < limit and use_builtin_fallback:
            needed = limit - len(matched_topics)
            builtin_topics = get_topics_by_matrix(ip_id, needed)
            for t in builtin_topics:
                t["source"] = "builtin"
            matched_topics.extend(builtin_topics)
        
        # 7. 四维评分
        for topic in matched_topics:
            topic["four_dim_score"] = self.matcher.calculate_four_dim_score(
                topic, ip_profile, weights
            )
        
        # 8. 按内容矩阵分配并排序
        final_topics = self._allocate_by_matrix(matched_topics, limit)
        
        # 9. 转换为推荐结果
        recommendations = [self._to_recommendation(t) for t in final_topics]
        
        return recommendations
    
    def _get_ip_profile(self, db: Session, ip_id: str) -> Optional[Dict[str, Any]]:
        """获取IP画像"""
        ip = db.query(IP).filter(IP.ip_id == ip_id).first()
        if not ip:
            return None
        
        return {
            "ip_id": ip_id,
            "name": ip.name,
            "nickname": ip.nickname or ip.name,
            "expertise": ip.expertise or "",
            "content_direction": ip.content_direction or "",
            "target_audience": ip.target_audience or "",
            "monetization_model": ip.monetization_model or "",
            "product_service": ip.product_service or "",
            "market_demand": ip.market_demand or "",
            "passion": ip.passion or "",
        }
    
    async def _fetch_all_sources(
        self,
        ip_id: str,
        ip_profile: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """并行获取多源数据"""
        topics = []
        
        # 尝试TIKHUB数据源
        if tikhub_client.is_configured():
            try:
                # 高播放榜
                tikhub_topics = await tikhub_client.get_recommended_topic_cards(limit=limit)
                for t in tikhub_topics:
                    t["source"] = "tikhub"
                topics.extend(tikhub_topics)
                logger.info(f"TIKHUB returned {len(tikhub_topics)} topics")
            except Exception as e:
                logger.warning(f"TIKHUB fetch failed: {e}")
        
        # 尝试douyin-hot-hub
        if len(topics) < limit:
            try:
                dyhub_topics = await douyin_hot_hub_client.get_recommended_topic_cards(limit=limit)
                for t in dyhub_topics:
                    t["source"] = "douyin-hot-hub"
                    t.setdefault("original_title", t.get("title", ""))
                topics.extend(dyhub_topics)
                logger.info(f"douyin-hot-hub returned {len(dyhub_topics)} topics")
            except Exception as e:
                logger.warning(f"douyin-hot-hub fetch failed: {e}")
        
        return topics
    
    def _allocate_by_matrix(
        self,
        topics: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        按4-3-2-1内容矩阵分配选题
        
        40% money + 30% emotion + 20% skill + 10% life
        """
        # 为每个话题分类
        for topic in topics:
            title = topic.get("title", "")
            topic["content_type"] = classify_content_type(title)
        
        # 按类型分组
        by_type = {"money": [], "emotion": [], "skill": [], "life": [], "other": []}
        for topic in topics:
            ctype = topic.get("content_type", "other")
            by_type[ctype].append(topic)
        
        # 按分数排序每类
        for ctype in by_type:
            by_type[ctype].sort(key=lambda x: x.get("four_dim_score", {}).get("total", 0), reverse=True)
        
        # 按矩阵比例选择
        matrix = {
            "money": int(limit * 0.4),
            "emotion": int(limit * 0.3),
            "skill": int(limit * 0.2),
            "life": limit - int(limit * 0.4) - int(limit * 0.3) - int(limit * 0.2),
        }
        
        result = []
        for ctype, count in matrix.items():
            selected = by_type[ctype][:count]
            # 如果某类不足，从other补充
            if len(selected) < count:
                needed = count - len(selected)
                selected.extend(by_type["other"][:needed])
            result.extend(selected)
        
        # 按综合分数排序
        result.sort(key=lambda x: x.get("four_dim_score", {}).get("total", 0), reverse=True)
        
        return result[:limit]
    
    def _get_builtin_recommendations(
        self,
        ip_id: str,
        limit: int,
        weights: Dict[str, float]
    ) -> List[TopicRecommendation]:
        """获取内置库推荐"""
        topics = get_topics_by_matrix(ip_id, limit)
        
        # 添加四维评分
        ip_profile = {"content_direction": "创业 女性"}  # 简化画像
        for topic in topics:
            topic["four_dim_score"] = self.matcher.calculate_four_dim_score(
                topic, ip_profile, weights
            )
        
        return [self._to_recommendation(t) for t in topics]
    
    def _get_generic_recommendations(
        self,
        ip_id: str,
        limit: int
    ) -> List[TopicRecommendation]:
        """获取通用推荐（当IP不存在时）"""
        topics = get_topics_by_matrix(ip_id, limit)
        return [self._to_recommendation(t) for t in topics]
    
    def _to_recommendation(self, topic: Dict[str, Any]) -> TopicRecommendation:
        """将原始数据转换为推荐结果"""
        content_type = topic.get("content_type", "other")
        four_dim = topic.get("four_dim_score", {})
        match_details = topic.get("match_details", {})
        
        return TopicRecommendation(
            id=topic.get("id", ""),
            title=topic.get("title", ""),
            original_title=topic.get("original_title", topic.get("originalTitle", topic.get("title", ""))),
            tags=topic.get("tags", []),
            score=four_dim.get("total", 4.0),
            match_score=match_details.get("overall", topic.get("match_score", 0.5)),
            four_dim_score=four_dim,
            content_type=content_type,
            content_type_name=get_content_type_name(content_type),
            source=topic.get("source", "unknown"),
            source_url=topic.get("sourceUrl", ""),
            reason=self._build_reason(topic),
            estimated_views=topic.get("estimatedViews", f"{int(topic.get('score', 4) * 5)}万+"),
            estimated_completion=topic.get("estimatedCompletion", 40),
        )
    
    def _build_reason(self, topic: Dict[str, Any]) -> str:
        """构建推荐理由"""
        source = topic.get("source", "unknown")
        content_type = topic.get("content_type", "other")
        match_score = topic.get("match_score", 0)
        
        if source == "builtin":
            return f"内置爆款库（{get_content_type_name(content_type)}）- 匹配度{match_score:.0%}"
        elif source == "tikhub":
            return f"TIKHUB热榜（{get_content_type_name(content_type)}）- 匹配度{match_score:.0%}"
        else:
            return f"大数据推荐（{get_content_type_name(content_type)}）- 匹配度{match_score:.0%}"


# 全局服务实例
_service: Optional[TopicRecommendationServiceV2] = None


def get_service() -> TopicRecommendationServiceV2:
    """获取全局服务实例"""
    global _service
    if _service is None:
        _service = TopicRecommendationServiceV2()
    return _service


# 便捷接口
async def recommend_topics_v2(
    db: Session,
    ip_id: str,
    limit: int = 12
) -> List[TopicRecommendation]:
    """
    推荐选题 V2 便捷接口
    
    使用示例:
        topics = await recommend_topics_v2(db, ip_id="xiaomin1", limit=12)
        for t in topics:
            print(f"{t.title} - 匹配度: {t.match_score:.0%}")
    """
    service = get_service()
    return await service.recommend_topics(db, ip_id, limit)
