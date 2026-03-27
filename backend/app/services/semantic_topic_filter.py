"""
语义相似度推荐服务
使用embedding模型计算IP与话题的相关性
"""
import os
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 尝试导入sentence-transformers，如果不可用则使用备选方案
SENTENCE_TRANSFORMERS_AVAILABLE = False
SentenceTransformer = None

try:
    import torch
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    logger.info("sentence-transformers loaded successfully")
except Exception as e:
    logger.warning(f"sentence-transformers not available: {e}, using keyword fallback")


class SemanticSimilarityFilter:
    """
    基于语义相似度的话题过滤
    """
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载embedding模型"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.info("Using keyword-based fallback for similarity")
            return
        
        try:
            # 使用多语言模型，支持中文
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}, using fallback")
            self.model = None
    
    def _get_ip_profile_text(self, ip_data: Dict) -> str:
        """将IP配置转为文本描述"""
        parts = []
        
        for field in ['expertise', 'content_direction', 'target_audience', 
                     'monetization_model', 'product_service', 'market_demand']:
            value = ip_data.get(field, '')
            if value:
                parts.append(str(value))
        
        return ' '.join(parts) if parts else ip_data.get('nickname', '')
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        if not self.model:
            return self._keyword_similarity(text1, text2)
        
        try:
            embeddings = self.model.encode([text1, text2])
            # 余弦相似度
            dot = sum(a * b for a, b in zip(embeddings[0], embeddings[1]))
            norm1 = sum(a * a for a in embeddings[0]) ** 0.5
            norm2 = sum(b * b for b in embeddings[1]) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot / (norm1 * norm2)
        except Exception as e:
            logger.warning(f"Embedding error: {e}")
            return self._keyword_similarity(text1, text2)
    
    def _keyword_similarity(self, text1: str, text2: str) -> float:
        """备选：关键词匹配相似度"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard相似度
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    def filter_topics(
        self,
        topics: List[Dict],
        ip_data: Dict,
        threshold: float = 0.3,
    ) -> List[Dict]:
        """
        过滤与IP相关的话题
        
        Args:
            topics: 原始话题列表
            ip_data: IP配置数据
            threshold: 相似度阈值，低于此值的话题会被过滤
        
        Returns:
            过滤后的话题列表，带有similarity_score
        """
        if not topics:
            return []
        
        # 获取IP的文本描述
        ip_text = self._get_ip_profile_text(ip_data)
        
        if not ip_text:
            logger.warning("No IP profile text, returning all topics")
            return topics
        
        filtered_topics = []
        
        for topic in topics:
            title = topic.get('title', '')
            tags = topic.get('tags', [])
            
            if not title:
                continue
            
            # 组合标题和标签作为话题文本
            topic_text = f"{title} {' '.join(tags)}" if tags else title
            
            # 计算相似度
            similarity = self.compute_similarity(ip_text, topic_text)
            
            # 只保留高于阈值的话题
            if similarity >= threshold:
                topic['similarity_score'] = round(similarity, 3)
                filtered_topics.append(topic)
        
        # 按相似度排序
        filtered_topics.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        logger.info(f"Filtered {len(filtered_topics)}/{len(topics)} topics (threshold={threshold})")
        
        return filtered_topics


# 全局实例
_semantic_filter: Optional[SemanticSimilarityFilter] = None


def get_semantic_filter() -> SemanticSimilarityFilter:
    """获取语义过滤实例"""
    global _semantic_filter
    
    if _semantic_filter is None:
        _semantic_filter = SemanticSimilarityFilter()
    
    return _semantic_filter


def filter_topics_by_similarity(
    topics: List[Dict],
    ip_data: Dict,
    threshold: float = 0.3,
) -> List[Dict]:
    """便捷函数：使用语义相似度过滤话题"""
    filter_instance = get_semantic_filter()
    return filter_instance.filter_topics(topics, ip_data, threshold)