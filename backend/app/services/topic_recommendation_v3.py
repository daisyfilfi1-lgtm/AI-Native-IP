"""
智能选题推荐服务 V3.0

核心改进：
1. 整合数据源层V2（多源融合）
2. 整合智能改写服务（解决机械拼接问题）
3. 统一的数据流：多源获取 -> 智能改写 -> 四维评分 -> 返回
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP
from app.services.strategy_config_service import get_merged_config
from app.services.datasource import get_datasource_manager_v2, TopicData
from app.services.enhanced_topic_matcher import get_matcher
from app.services.topic_rewrite_service import get_rewrite_service, RewriteStrategy
from app.services.keyword_synonyms import classify_content_type, get_content_type_name

logger = logging.getLogger(__name__)


@dataclass
class TopicRecommendationV3:
    """选题推荐结果 V3"""
    id: str
    title: str                    # 改写后的标题（符合IP定位）
    original_title: str           # 原标题（保留溯源）
    platform: str                 # 来源平台
    tags: List[str]
    score: float                  # 四维综合分
    match_score: float            # IP匹配度
    content_type: str             # money/emotion/skill/life
    content_type_name: str
    source: str                   # 数据来源
    source_url: str
    
    # 改写相关信息
    rewrite_strategy: str         # 改写策略
    rewrite_quality: float        # 改写质量分
    rewrite_reason: str           # 改写说明
    
    # 四维评分
    four_dim_score: Dict[str, float]


class TopicRecommendationServiceV3:
    """
    选题推荐服务 V3.0
    
    完整流程：
    1. 从多数据源获取原始话题
    2. 智能改写（解决原系统的机械拼接问题）
    3. IP匹配评分
    4. 四维评分
    5. 内容矩阵分配
    6. 返回
    """
    
    def __init__(self):
        self.datasource_manager = get_datasource_manager_v2()
        self.matcher = get_matcher()
        self.rewrite_service = get_rewrite_service()
    
    async def recommend_topics(
        self,
        db: Session,
        ip_id: str,
        limit: int = 12,
        strategy: str = "smart",           # 数据源策略
        rewrite_strategy: str = "smart",   # 改写策略
        min_rewrite_quality: float = 0.5   # 最低改写质量
    ) -> List[TopicRecommendationV3]:
        """
        推荐话题主入口
        
        Args:
            db: 数据库会话
            ip_id: IP ID
            limit: 返回数量
            strategy: 数据源获取策略
            rewrite_strategy: 改写策略
            min_rewrite_quality: 最低改写质量阈值
        """
        # 1. 获取IP画像
        ip_profile = self._get_ip_profile(db, ip_id)
        if not ip_profile:
            logger.warning(f"IP not found: {ip_id}, using generic topics")
            return self._get_generic_recommendations(ip_id, limit)
        
        # 2. 获取策略配置
        config = get_merged_config(db, ip_id)
        weights = config.get("four_dim_weights", {
            "relevance": 0.3, "hotness": 0.3, "competition": 0.2, "conversion": 0.2
        })
        
        # 3. 从多数据源获取原始话题
        raw_topics = await self._fetch_raw_topics(ip_profile, limit * 2, strategy)
        
        if not raw_topics:
            logger.warning(f"No raw topics fetched for {ip_id}, using builtin")
            return self._get_builtin_recommendations(ip_id, limit, weights)
        
        # 4. 智能改写（核心改进）
        rewritten_topics = await self._smart_rewrite(
            raw_topics, ip_profile, rewrite_strategy, min_rewrite_quality
        )
        
        # 5. IP匹配评分
        matched_topics = self._score_and_match(rewritten_topics, ip_profile)
        
        # 6. 四维评分
        scored_topics = self._calculate_four_dim_scores(matched_topics, ip_profile, weights)
        
        # 7. 内容矩阵分配
        final_topics = self._allocate_by_matrix(scored_topics, limit)
        
        # 8. 转换为推荐结果
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
    
    async def _fetch_raw_topics(
        self,
        ip_profile: Dict[str, Any],
        limit: int,
        strategy: str
    ) -> List[Dict[str, Any]]:
        """从多数据源获取原始话题"""
        try:
            # 使用数据源管理器V2
            topic_data_list = await self.datasource_manager.fetch_with_strategy(
                ip_profile, limit, strategy
            )
            
            # 转换为字典格式
            topics = []
            for td in topic_data_list:
                topics.append({
                    "id": td.id,
                    "title": td.title,
                    "original_title": td.original_title,
                    "platform": td.platform,
                    "url": td.url,
                    "tags": td.tags,
                    "score": td.score,
                    "source": td.source,
                    "extra": td.extra,
                })
            
            logger.info(f"[V3] Fetched {len(topics)} raw topics")
            return topics
            
        except Exception as e:
            logger.error(f"[V3] Failed to fetch raw topics: {e}")
            return []
    
    async def _smart_rewrite(
        self,
        topics: List[Dict[str, Any]],
        ip_profile: Dict[str, Any],
        strategy: str,
        min_quality: float
    ) -> List[Dict[str, Any]]:
        """
        智能改写话题
        
        核心改进：解决原系统的机械拼接问题
        """
        rewrite_strategy = RewriteStrategy.TEMPLATE_SMART
        if strategy == "llm":
            rewrite_strategy = RewriteStrategy.LLM_SEMANTIC
        
        rewritten = []
        
        for topic in topics:
            original_title = topic.get("title", "")
            
            # 检查是否来自内置库（已经是高质量，不需要改写）
            if topic.get("source") == "builtin":
                topic["original_title"] = original_title
                topic["rewrite_strategy"] = "builtin_no_rewrite"
                topic["rewrite_quality"] = 0.95
                topic["rewrite_reason"] = "内置库精选，无需改写"
                rewritten.append(topic)
                continue
            
            # 检查是否已经符合IP定位
            if self._is_already_ip_matched(original_title, ip_profile):
                topic["original_title"] = original_title
                topic["rewrite_strategy"] = "already_matched"
                topic["rewrite_quality"] = 0.9
                topic["rewrite_reason"] = "原标题已符合IP定位"
                rewritten.append(topic)
                continue
            
            # 使用改写服务
            try:
                result = self.rewrite_service.rewrite_topic(
                    original_title, ip_profile, rewrite_strategy
                )
                
                # 如果质量不达标，使用保底标题
                if result.quality_score < min_quality:
                    logger.info(f"[V3] Low quality ({result.quality_score:.2f}) for '{original_title}'")
                    # 使用内置库生成替代标题
                    fallback = self._generate_fallback_title(result.content_type, ip_profile)
                    topic["title"] = fallback
                    topic["rewrite_strategy"] = "fallback_generated"
                    topic["rewrite_quality"] = 0.7
                    topic["rewrite_reason"] = f"原标题'{original_title}'改写质量不佳，使用IP专属标题"
                else:
                    topic["title"] = result.rewritten_title
                    topic["rewrite_strategy"] = result.strategy.value
                    topic["rewrite_quality"] = result.quality_score
                    topic["rewrite_reason"] = result.reason
                
                topic["original_title"] = original_title
                topic["content_type"] = result.content_type
                
            except Exception as e:
                logger.warning(f"[V3] Rewrite failed for '{original_title}': {e}")
                # 失败时保留原标题
                topic["original_title"] = original_title
                topic["rewrite_strategy"] = "rewrite_failed"
                topic["rewrite_quality"] = 0.3
                topic["rewrite_reason"] = f"改写失败: {str(e)}"
            
            rewritten.append(topic)
        
        return rewritten
    
    def _is_already_ip_matched(self, title: str, ip_profile: Dict[str, Any]) -> bool:
        """检查标题是否已经符合IP定位"""
        # 提取IP关键词
        ip_text = " ".join([
            ip_profile.get("expertise", ""),
            ip_profile.get("content_direction", ""),
            ip_profile.get("target_audience", ""),
        ])
        
        # 简单关键词匹配
        ip_keywords = ["宝妈", "创业", "女性", "馒头", "花样馒头", "副业", "月入"]
        matched = [kw for kw in ip_keywords if kw in ip_text and kw in title]
        
        return len(matched) >= 2
    
    def _generate_fallback_title(self, content_type: str, ip_profile: Dict[str, Any]) -> str:
        """生成保底标题"""
        nickname = ip_profile.get("nickname", "她")
        
        templates = {
            "money": f"从0到月入3万：这个{nickname}的创业方法太绝了",
            "emotion": f"从负债到逆袭：一个{nickname}如何用创业重启人生",
            "skill": f"手艺变现金：她用{nickname}的绝活做到月入3万",
            "life": f"创业后的{nickname}，终于活成了自己想要的样子",
        }
        
        return templates.get(content_type, f"{nickname}的创业故事")
    
    def _score_and_match(
        self,
        topics: List[Dict[str, Any]],
        ip_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """IP匹配评分"""
        for topic in topics:
            match_scores = self.matcher.compute_match_score(ip_profile, {
                "title": topic.get("title", ""),
                "tags": topic.get("tags", []),
            })
            topic["match_score"] = match_scores["overall"]
            topic["match_details"] = match_scores
        
        # 按匹配度排序
        topics.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        return topics
    
    def _calculate_four_dim_scores(
        self,
        topics: List[Dict[str, Any]],
        ip_profile: Dict[str, Any],
        weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """计算四维评分"""
        for topic in topics:
            four_dim = self.matcher.calculate_four_dim_score(topic, ip_profile, weights)
            topic["four_dim_score"] = four_dim
            topic["score"] = four_dim["total"]  # 综合分
        
        return topics
    
    def _allocate_by_matrix(
        self,
        topics: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """按4-3-2-1内容矩阵分配"""
        # 确保每个话题有content_type
        for topic in topics:
            if "content_type" not in topic:
                topic["content_type"] = classify_content_type(topic.get("title", ""))
        
        # 按类型分组
        by_type = {"money": [], "emotion": [], "skill": [], "life": [], "other": []}
        for topic in topics:
            ctype = topic.get("content_type", "other")
            by_type[ctype].append(topic)
        
        # 按分数排序
        for ctype in by_type:
            by_type[ctype].sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # 按矩阵比例选择
        matrix = {
            "money": int(limit * 0.4),
            "emotion": int(limit * 0.3),
            "skill": int(limit * 0.2),
            "life": max(1, limit - int(limit * 0.4) - int(limit * 0.3) - int(limit * 0.2)),
        }
        
        result = []
        for ctype, count in matrix.items():
            selected = by_type[ctype][:count]
            # 如果某类不足，从other补充
            if len(selected) < count:
                needed = count - len(selected)
                selected.extend(by_type["other"][:needed])
            result.extend(selected)
        
        # 按综合分排序
        result.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return result[:limit]
    
    def _to_recommendation(self, topic: Dict[str, Any]) -> TopicRecommendationV3:
        """转换为推荐结果"""
        content_type = topic.get("content_type", "other")
        four_dim = topic.get("four_dim_score", {})
        
        return TopicRecommendationV3(
            id=topic.get("id", ""),
            title=topic.get("title", ""),
            original_title=topic.get("original_title", topic.get("title", "")),
            platform=topic.get("platform", ""),
            tags=topic.get("tags", []),
            score=four_dim.get("total", 4.0),
            match_score=topic.get("match_score", 0.5),
            content_type=content_type,
            content_type_name=get_content_type_name(content_type),
            source=topic.get("source", ""),
            source_url=topic.get("url", ""),
            rewrite_strategy=topic.get("rewrite_strategy", ""),
            rewrite_quality=topic.get("rewrite_quality", 0.5),
            rewrite_reason=topic.get("rewrite_reason", ""),
            four_dim_score=four_dim,
        )
    
    def _get_generic_recommendations(
        self,
        ip_id: str,
        limit: int
    ) -> List[TopicRecommendationV3]:
        """获取通用推荐"""
        # 使用内置库
        from app.services.datasource.builtin_source import get_builtin_topics
        
        topics = get_builtin_topics(ip_id, limit=limit)
        
        recommendations = []
        for t in topics:
            rec = TopicRecommendationV3(
                id=t.get("id", ""),
                title=t.get("title", ""),
                original_title=t.get("title", ""),
                platform="builtin",
                tags=t.get("tags", []),
                score=t.get("score", 4.0),
                match_score=0.9,
                content_type=t.get("content_type", "other"),
                content_type_name=get_content_type_name(t.get("content_type", "other")),
                source="builtin",
                source_url="",
                rewrite_strategy="builtin_no_rewrite",
                rewrite_quality=0.95,
                rewrite_reason="内置精选，无需改写",
                four_dim_score={
                    "total": t.get("score", 4.0),
                    "relevance": 0.9,
                    "hotness": 0.9,
                    "competition": 0.5,
                    "conversion": 0.8,
                }
            )
            recommendations.append(rec)
        
        return recommendations
    
    def _get_builtin_recommendations(
        self,
        ip_id: str,
        limit: int,
        weights: Dict[str, float]
    ) -> List[TopicRecommendationV3]:
        """获取内置库推荐"""
        return self._get_generic_recommendations(ip_id, limit)


# 全局实例
_service_v3: Optional[TopicRecommendationServiceV3] = None


def get_service_v3() -> TopicRecommendationServiceV3:
    """获取V3服务实例"""
    global _service_v3
    if _service_v3 is None:
        _service_v3 = TopicRecommendationServiceV3()
    return _service_v3


async def recommend_topics_v3(
    db: Session,
    ip_id: str,
    limit: int = 12
) -> List[TopicRecommendationV3]:
    """便捷函数：V3推荐"""
    service = get_service_v3()
    return await service.recommend_topics(db, ip_id, limit)
