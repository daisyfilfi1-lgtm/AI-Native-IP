"""
增强版IP话题匹配服务
结合语义匹配、关键词扩展、多维评分
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
import re

from app.services.keyword_synonyms import (
    expand_keywords, 
    calculate_keyword_match_score,
    classify_content_type,
    get_content_type_name,
    CONTENT_TYPE_KEYWORDS,
)

logger = logging.getLogger(__name__)

# 尝试导入sentence-transformers
SENTENCE_TRANSFORMERS_AVAILABLE = False
SentenceTransformer = None
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    logger.info("sentence-transformers available")
except Exception as e:
    logger.warning(f"sentence-transformers not available: {e}, using keyword-based matching")


class EnhancedTopicMatcher:
    """
    增强版IP话题匹配器
    支持语义相似度、关键词扩展、多维匹配
    """
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self.model = None
        self._model_loaded = False
        
        # 缓存IP的embedding向量
        self._ip_embedding_cache: Dict[str, List[float]] = {}
    
    def _load_model(self):
        """懒加载embedding模型"""
        if self._model_loaded or not SENTENCE_TRANSFORMERS_AVAILABLE:
            return
        
        try:
            self.model = SentenceTransformer(self.model_name)
            self._model_loaded = True
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
            self._model_loaded = True  # 标记为已尝试，不再重试
    
    def _get_ip_profile_text(self, ip_profile: Dict[str, Any]) -> str:
        """将IP画像转换为文本描述"""
        parts = []
        
        # 核心字段
        fields = [
            ip_profile.get("expertise", ""),
            ip_profile.get("content_direction", ""),
            ip_profile.get("target_audience", ""),
            ip_profile.get("monetization_model", ""),
            ip_profile.get("product_service", ""),
            ip_profile.get("market_demand", ""),
            ip_profile.get("passion", ""),
            ip_profile.get("nickname", ""),
        ]
        
        for field in fields:
            if field and isinstance(field, str):
                parts.append(field)
        
        return " ".join(parts)
    
    def _get_ip_keywords(self, ip_profile: Dict[str, Any]) -> List[str]:
        """从IP画像提取关键词"""
        keywords = []
        
        text = self._get_ip_profile_text(ip_profile)
        
        # 提取中文关键词（2-8字）
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,8}', text)
        keywords.extend(chinese_words)
        
        # 添加核心关键词（如果文本中包含）
        core_keywords = [
            "宝妈", "创业", "女性", "赚钱", "馒头", "花样馒头",
            "副业", "变现", "私域", "手艺", "摆摊", "低成本"
        ]
        for kw in core_keywords:
            if kw in text and kw not in keywords:
                keywords.append(kw)
        
        # 去重并保持顺序
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen and len(kw) >= 2:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:20]
    
    def compute_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的语义相似度
        
        Returns:
            相似度分数 (0.0 - 1.0)
        """
        self._load_model()
        
        if not self.model or not text1 or not text2:
            # 回退到关键词匹配
            return self._keyword_similarity(text1, text2)
        
        try:
            embeddings = self.model.encode([text1, text2])
            
            # 余弦相似度
            dot = sum(a * b for a, b in zip(embeddings[0], embeddings[1]))
            norm1 = sum(a * a for a in embeddings[0]) ** 0.5
            norm2 = sum(b * b for b in embeddings[1]) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot / (norm1 * norm2))
        except Exception as e:
            logger.warning(f"Semantic similarity failed: {e}")
            return self._keyword_similarity(text1, text2)
    
    def _keyword_similarity(self, text1: str, text2: str) -> float:
        """基于关键词的相似度（Jaccard）"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def compute_match_score(
        self,
        ip_profile: Dict[str, Any],
        topic: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        计算IP与话题的综合匹配分数
        
        Args:
            ip_profile: IP画像
            topic: 话题数据
            
        Returns:
            {
                "overall": float,       # 综合匹配度 (0-1)
                "semantic": float,      # 语义相似度 (0-1)
                "keyword": float,       # 关键词匹配度 (0-1)
                "audience": float,      # 受众匹配度 (0-1)
                "intent": float,        # 意图匹配度 (0-1)
            }
        """
        # 提取文本
        ip_text = self._get_ip_profile_text(ip_profile)
        ip_keywords = self._get_ip_keywords(ip_profile)
        
        topic_title = topic.get("title", "")
        topic_tags = " ".join(topic.get("tags", []))
        topic_text = f"{topic_title} {topic_tags}"
        
        # 1. 语义相似度 (30%)
        semantic_score = self.compute_semantic_similarity(ip_text, topic_text)
        
        # 2. 关键词匹配度 (40%)
        keyword_score = calculate_keyword_match_score(topic_text, ip_keywords)
        
        # 3. 受众匹配度 (20%)
        audience_score = self._compute_audience_match(
            ip_profile.get("target_audience", ""),
            topic_title
        )
        
        # 4. 意图匹配度 (10%)
        intent_score = self._compute_intent_match(ip_profile, topic)
        
        # 综合分数（加权平均）
        overall = (
            semantic_score * 0.3 +
            keyword_score * 0.4 +
            audience_score * 0.2 +
            intent_score * 0.1
        )
        
        return {
            "overall": round(min(1.0, max(0.0, overall)), 3),
            "semantic": round(semantic_score, 3),
            "keyword": round(keyword_score, 3),
            "audience": round(audience_score, 3),
            "intent": round(intent_score, 3),
        }
    
    def _compute_audience_match(self, target_audience: str, topic_title: str) -> float:
        """计算受众匹配度"""
        if not target_audience:
            return 0.5
        
        audience_keywords = expand_keywords([target_audience])
        
        matched = sum(1 for kw in audience_keywords if kw.lower() in topic_title.lower())
        
        return min(1.0, matched / 3)
    
    def _compute_intent_match(self, ip_profile: Dict[str, Any], topic: Dict[str, Any]) -> float:
        """计算意图匹配度（内容类型是否符合IP方向）"""
        content_dir = ip_profile.get("content_direction", "").lower()
        topic_title = topic.get("title", "").lower()
        
        # 分析内容类型
        topic_type = classify_content_type(topic_title)
        
        # 检查IP方向是否包含相关内容
        scores = []
        
        if "创业" in content_dir or "赚钱" in content_dir:
            if topic_type == "money":
                scores.append(1.0)
        
        if "女性" in content_dir or "独立" in content_dir:
            if topic_type == "emotion":
                scores.append(0.9)
        
        if "手艺" in content_dir or "技能" in content_dir:
            if topic_type == "skill":
                scores.append(1.0)
        
        if not scores:
            return 0.5
        
        return sum(scores) / len(scores)
    
    def filter_and_rank_topics(
        self,
        ip_profile: Dict[str, Any],
        topics: List[Dict[str, Any]],
        threshold: float = 0.3,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        过滤并排序话题
        
        Args:
            ip_profile: IP画像
            topics: 话题列表
            threshold: 匹配度阈值
            top_k: 返回数量
            
        Returns:
            排序后的话题列表
        """
        scored_topics = []
        
        for topic in topics:
            match_scores = self.compute_match_score(ip_profile, topic)
            
            if match_scores["overall"] >= threshold:
                topic["match_score"] = match_scores["overall"]
                topic["match_details"] = match_scores
                scored_topics.append(topic)
        
        # 按匹配度排序
        scored_topics.sort(key=lambda x: x["match_score"], reverse=True)
        
        return scored_topics[:top_k]
    
    def calculate_four_dim_score(
        self,
        topic: Dict[str, Any],
        ip_profile: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """
        计算四维评分
        
        Args:
            topic: 话题
            ip_profile: IP画像
            weights: 权重配置 {"relevance": 0.3, "hotness": 0.3, "competition": 0.2, "conversion": 0.2}
            
        Returns:
            四维评分结果
        """
        default_weights = {"relevance": 0.3, "hotness": 0.3, "competition": 0.2, "conversion": 0.2}
        weights = weights or default_weights
        
        # 1. 相关度 (relevance) - 与IP的匹配程度
        match_score = topic.get("match_score", 0.5)
        relevance = match_score
        
        # 2. 热度 (hotness) - 话题的火爆程度
        base_score = topic.get("score", 4.0)
        hotness = min(1.0, base_score / 5.0)
        
        # 3. 竞争度 (competition) - 越低越好
        # 假设热度高的竞争激烈
        competition = max(0.0, 1.0 - hotness * 0.5)
        
        # 4. 转化度 (conversion) - 是否容易引导变现
        title = topic.get("title", "")
        conversion_keywords = ["赚钱", "变现", "月入", "成交", "转化", "副业", "创业"]
        conversion = 0.5
        for kw in conversion_keywords:
            if kw in title:
                conversion = 0.9
                break
        
        # 加权总分
        total = (
            relevance * weights.get("relevance", 0.3) +
            hotness * weights.get("hotness", 0.3) +
            competition * weights.get("competition", 0.2) +
            conversion * weights.get("conversion", 0.2)
        )
        
        return {
            "total": round(total * 5.0, 2),  # 转换为0-5分制
            "relevance": round(relevance, 2),
            "hotness": round(hotness, 2),
            "competition": round(competition, 2),
            "conversion": round(conversion, 2),
        }


# 全局匹配器实例
_matcher: Optional[EnhancedTopicMatcher] = None


def get_matcher() -> EnhancedTopicMatcher:
    """获取全局匹配器实例"""
    global _matcher
    if _matcher is None:
        _matcher = EnhancedTopicMatcher()
    return _matcher


def quick_match(
    ip_profile: Dict[str, Any],
    topic: Dict[str, Any]
) -> float:
    """快速匹配接口，返回综合匹配分数"""
    matcher = get_matcher()
    scores = matcher.compute_match_score(ip_profile, topic)
    return scores["overall"]
