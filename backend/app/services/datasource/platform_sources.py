"""
平台专属数据源

包含：
1. 小红书专属数据源 - 聚合多个小红书API
2. 抖音专属数据源 - 聚合多个抖音API
"""

import logging
from typing import List, Dict, Any, Optional
import httpx
import os

from .base import DataSource, DataSourceConfig, TopicData, DataSourcePriority

logger = logging.getLogger(__name__)


class XiaohongshuDataSource(DataSource):
    """
    小红书专属数据源
    
    聚合多个小红书数据API：
    1. 顺为数据 (api.itapi.cn) - 10元/月
    2. DailyHot API - 免费/自部署
    3. 今日热榜 (tophubdata.com) - 免费+付费
    4. VVhan API - 免费
    
    按优先级自动选择可用的API
    """
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="xiaohongshu_aggregated",
            name="小红书聚合数据源",
            priority=DataSourcePriority.P0,
            enabled=True,
            timeout=15,
            max_results=20,
            cache_ttl=600,
        )
        super().__init__(config)
        
        # 初始化子数据源
        self._sources = []
        
        # 优先尝试付费源（如果有配置）
        if os.environ.get("SHUNWEI_API_KEY"):
            from .paid_sources import ShunWeiDataSource
            self._sources.append(("shunwei", ShunWeiDataSource()))
        
        # 然后尝试免费源
        from .free_sources import DailyHotDataSource, VVhanDataSource
        self._sources.append(("dailyhot", DailyHotDataSource()))
        self._sources.append(("vvhan", VVhanDataSource()))
    
    def is_available(self) -> bool:
        """只要有一个子源可用就返回True"""
        return len(self._sources) > 0
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """从小红书获取数据"""
        all_topics = []
        
        for name, source in self._sources:
            if len(all_topics) >= limit:
                break
            
            try:
                if not source.is_available():
                    continue
                
                topics = await source.fetch(ip_profile, limit - len(all_topics))
                
                # 筛选小红书相关数据
                xhs_topics = [t for t in topics if self._is_xiaohongshu_related(t)]
                
                # 标记来源
                for t in xhs_topics:
                    t.source = f"xiaohongshu_{name}"
                    t.platform = "xiaohongshu"
                
                all_topics.extend(xhs_topics)
                
                if xhs_topics:
                    logger.info(f"[Xiaohongshu] Got {len(xhs_topics)} topics from {name}")
                
            except Exception as e:
                logger.warning(f"[Xiaohongshu] Source {name} failed: {e}")
                continue
        
        return all_topics[:limit]
    
    def _is_xiaohongshu_related(self, topic: TopicData) -> bool:
        """判断是否是小红书相关内容"""
        # 平台匹配
        if topic.platform in ["xiaohongshu", "xiaohongshu_topic"]:
            return True
        
        # 标签匹配
        xhs_tags = ["小红书", "xhs", "XHS", "redbook"]
        if any(tag in topic.tags for tag in xhs_tags):
            return True
        
        # 标题匹配小红书风格
        xhs_keywords = ["姐妹", "种草", "拔草", "攻略", "测评", "分享"]
        if any(kw in topic.title for kw in xhs_keywords):
            return True
        
        return False


class DouyinDataSource(DataSource):
    """
    抖音专属数据源
    
    聚合多个抖音数据API：
    1. TIKHUB - 需要企业资质
    2. 顺为数据 - 10元/月
    3. DailyHot API - 免费/自部署
    4. 抖音免费API - aa1.cn等
    5. VVhan API - 免费
    
    按优先级自动选择可用的API
    """
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="douyin_aggregated",
            name="抖音聚合数据源",
            priority=DataSourcePriority.P0,
            enabled=True,
            timeout=15,
            max_results=20,
            cache_ttl=600,
        )
        super().__init__(config)
        
        self._sources = []
        
        # TIKHUB（优先级最高，但需要企业资质）
        if os.environ.get("TIKHUB_API_KEY"):
            from .tikhub_source import TikHubDataSource
            self._sources.append(("tikhub", TikHubDataSource()))
        
        # 顺为数据
        if os.environ.get("SHUNWEI_API_KEY"):
            from .paid_sources import ShunWeiDataSource
            self._sources.append(("shunwei", ShunWeiDataSource()))
        
        # 免费源
        from .free_sources import DailyHotDataSource, DouyinHotDataSource, VVhanDataSource
        self._sources.append(("dailyhot", DailyHotDataSource()))
        self._sources.append(("douyin_free", DouyinHotDataSource()))
        self._sources.append(("vvhan", VVhanDataSource()))
    
    def is_available(self) -> bool:
        return len(self._sources) > 0
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """从抖音获取数据"""
        all_topics = []
        
        for name, source in self._sources:
            if len(all_topics) >= limit:
                break
            
            try:
                if not source.is_available():
                    continue
                
                topics = await source.fetch(ip_profile, limit - len(all_topics))
                
                # 筛选抖音相关数据
                dy_topics = [t for t in topics if self._is_douyin_related(t)]
                
                # 标记来源
                for t in dy_topics:
                    t.source = f"douyin_{name}"
                    t.platform = "douyin"
                
                all_topics.extend(dy_topics)
                
                if dy_topics:
                    logger.info(f"[Douyin] Got {len(dy_topics)} topics from {name}")
                
            except Exception as e:
                logger.warning(f"[Douyin] Source {name} failed: {e}")
                continue
        
        return all_topics[:limit]
    
    def _is_douyin_related(self, topic: TopicData) -> bool:
        """判断是否是抖音相关内容"""
        if topic.platform in ["douyin", "douyin_hot", "dy"]:
            return True
        
        douyin_tags = ["抖音", "douyin", "DY", "短视频"]
        if any(tag in topic.tags for tag in douyin_tags):
            return True
        
        return False


class WeiboDataSource(DataSource):
    """
    微博专属数据源
    
    微博是重要的热点来源
    """
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="weibo_aggregated",
            name="微博聚合数据源",
            priority=DataSourcePriority.P1,
            enabled=True,
            timeout=10,
            max_results=15,
            cache_ttl=600,
        )
        super().__init__(config)
        
        self._sources = []
        
        # 免费微博API
        from .free_sources import WeiboHotDataSource, DailyHotDataSource, VVhanDataSource
        self._sources.append(("weibo_free", WeiboHotDataSource()))
        self._sources.append(("dailyhot", DailyHotDataSource()))
        self._sources.append(("vvhan", VVhanDataSource()))
    
    def is_available(self) -> bool:
        return len(self._sources) > 0
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """从微博获取数据"""
        all_topics = []
        
        for name, source in self._sources:
            if len(all_topics) >= limit:
                break
            
            try:
                if not source.is_available():
                    continue
                
                topics = await source.fetch(ip_profile, limit - len(all_topics))
                weibo_topics = [t for t in topics if self._is_weibo_related(t)]
                
                for t in weibo_topics:
                    t.source = f"weibo_{name}"
                    t.platform = "weibo"
                
                all_topics.extend(weibo_topics)
                
            except Exception as e:
                logger.warning(f"[Weibo] Source {name} failed: {e}")
                continue
        
        return all_topics[:limit]
    
    def _is_weibo_related(self, topic: TopicData) -> bool:
        """判断是否是微博相关内容"""
        if topic.platform in ["weibo", "weibo_hot"]:
            return True
        
        if "微博" in topic.tags or "weibo" in topic.tags:
            return True
        
        return False


class ZhihuDataSource(DataSource):
    """
    知乎专属数据源
    
    知乎热榜是高质量内容来源
    """
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="zhihu_aggregated",
            name="知乎聚合数据源",
            priority=DataSourcePriority.P2,
            enabled=True,
            timeout=10,
            max_results=10,
            cache_ttl=1800,
        )
        super().__init__(config)
        
        self._sources = []
        
        from .free_sources import DailyHotDataSource, VVhanDataSource
        self._sources.append(("dailyhot", DailyHotDataSource()))
        self._sources.append(("vvhan", VVhanDataSource()))
    
    def is_available(self) -> bool:
        return len(self._sources) > 0
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """从知乎获取数据"""
        all_topics = []
        
        for name, source in self._sources:
            if len(all_topics) >= limit:
                break
            
            try:
                topics = await source.fetch(ip_profile, limit - len(all_topics))
                zhihu_topics = [t for t in topics if t.platform in ["zhihu", "zhihu_daily"]]
                
                for t in zhihu_topics:
                    t.source = f"zhihu_{name}"
                    t.platform = "zhihu"
                
                all_topics.extend(zhihu_topics)
                
            except Exception as e:
                logger.warning(f"[Zhihu] Source {name} failed: {e}")
                continue
        
        return all_topics[:limit]


class BilibiliDataSource(DataSource):
    """
    B站专属数据源
    
    B站是年轻用户聚集平台
    """
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="bilibili_aggregated",
            name="B站聚合数据源",
            priority=DataSourcePriority.P2,
            enabled=True,
            timeout=10,
            max_results=10,
            cache_ttl=1800,
        )
        super().__init__(config)
        
        self._sources = []
        
        from .free_sources import DailyHotDataSource, VVhanDataSource
        self._sources.append(("dailyhot", DailyHotDataSource()))
        self._sources.append(("vvhan", VVhanDataSource()))
    
    def is_available(self) -> bool:
        return len(self._sources) > 0
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """从B站获取数据"""
        all_topics = []
        
        for name, source in self._sources:
            if len(all_topics) >= limit:
                break
            
            try:
                topics = await source.fetch(ip_profile, limit - len(all_topics))
                bili_topics = [t for t in topics if t.platform in ["bilibili", "bili"]]
                
                for t in bili_topics:
                    t.source = f"bilibili_{name}"
                    t.platform = "bilibili"
                
                all_topics.extend(bili_topics)
                
            except Exception as e:
                logger.warning(f"[Bilibili] Source {name} failed: {e}")
                continue
        
        return all_topics[:limit]
