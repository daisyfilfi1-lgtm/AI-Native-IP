"""
TIKHUB数据源

设计要点：
1. 带缓存策略，减少API调用
2. 健康检查，自动降级
3. 多接口聚合（高播榜+低粉榜+话题）
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from .base import DataSource, DataSourceConfig, TopicData, DataSourcePriority
from .cache import TopicCache

logger = logging.getLogger(__name__)


class TikHubDataSource(DataSource):
    """
    TIKHUB数据源
    
    优先获取实时数据，失败时从缓存读取
    """
    
    def __init__(self, config: Optional[DataSourceConfig] = None):
        if config is None:
            config = DataSourceConfig(
                source_id="tikhub",
                name="TIKHUB热榜",
                priority=DataSourcePriority.P2,
                enabled=True,
                timeout=15,
                max_results=20,
                cache_ttl=1800,  # 30分钟缓存
                fallback_sources=["builtin"]
            )
        super().__init__(config)
        
        self.api_key = os.environ.get("TIKHUB_API_KEY", "")
        self.cache = TopicCache()
        self._available = bool(self.api_key)
        
        if not self._available:
            logger.warning("[TikHubSource] TIKHUB_API_KEY not configured")
    
    def is_available(self) -> bool:
        """检查TIKHUB是否配置"""
        return self._available and self.config.enabled
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """
        从TIKHUB获取数据
        
        策略：
        1. 先查缓存
        2. 缓存 miss 或过期，调用API
        3. API失败，返回缓存（即使过期）
        """
        ip_id = ip_profile.get("ip_id", "default")
        
        # 检查缓存
        cache_ttl = self.config.cache_ttl // 3600  # 转为小时
        cached_topics = self.cache.get(ip_id, self.source_id, max_age_hours=cache_ttl)
        
        if cached_topics:
            logger.info(f"[TikHubSource] Returning {len(cached_topics)} cached topics")
            return cached_topics[:limit]
        
        # 调用API
        try:
            topics = await self._fetch_from_api(ip_profile, limit)
            
            # 写入缓存
            if topics:
                self.cache.set(ip_id, self.source_id, topics)
            
            return topics
            
        except Exception as e:
            logger.error(f"[TikHubSource] API failed: {e}")
            self._record_error(str(e))
            
            # 返回过期缓存（如果有）
            stale_topics = self.cache.get(ip_id, self.source_id, max_age_hours=cache_ttl * 2)
            if stale_topics:
                logger.info(f"[TikHubSource] Returning {len(stale_topics)} stale cached topics")
                return stale_topics[:limit]
            
            return []
    
    async def _fetch_from_api(
        self, 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[TopicData]:
        """从TIKHUB API获取数据"""
        from app.services import tikhub_client
        
        if not tikhub_client.is_configured():
            raise Exception("TIKHUB not configured")
        
        # 获取高播放榜
        try:
            raw_data = await tikhub_client.fetch_douyin_high_play_hot_list(
                page=1, page_size=min(limit * 2, 30)
            )
            
            # 解析数据
            cards = tikhub_client.billboard_to_topic_cards(raw_data, limit=limit)
            
            topics = []
            for card in cards:
                topic = TopicData(
                    id=card.get("id", ""),
                    title=card.get("title", ""),
                    original_title=card.get("originalTitle", card.get("title", "")),
                    platform="douyin",
                    url=card.get("sourceUrl", ""),
                    tags=card.get("tags", ["抖音", "热榜"]),
                    score=float(card.get("score", 4.0)),
                    source="tikhub",
                )
                topics.append(topic)
            
            logger.info(f"[TikHubSource] Fetched {len(topics)} topics from API")
            return topics
            
        except Exception as e:
            logger.error(f"[TikHubSource] Failed to fetch from API: {e}")
            raise
