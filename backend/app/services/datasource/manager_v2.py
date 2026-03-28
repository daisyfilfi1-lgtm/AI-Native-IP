"""
数据源管理器 V2

包含所有可用的数据源：
- 免费/开源源
- 付费开发者源  
- 平台专属聚合源
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from .base import (
    DataSource, DataSourceConfig, TopicData,
    DataSourcePriority, DataSourceStatus
)
from .cache import TopicCache

# 导入所有数据源
from .builtin_source import BuiltinDataSource
from .tikhub_source import TikHubDataSource
from .free_sources import (
    DailyHotDataSource,
    VVhanDataSource,
    WeiboHotDataSource,
    DouyinHotDataSource,
)
from .paid_sources import (
    ShunWeiDataSource,
    QQLYKMDataSource,
    TopHubDataSource,
)
from .platform_sources import (
    XiaohongshuDataSource,
    DouyinDataSource,
    WeiboDataSource,
    ZhihuDataSource,
    BilibiliDataSource,
)

logger = logging.getLogger(__name__)


class DataSourceManagerV2:
    """
    数据源管理器 V2
    
    功能：
    - 自动注册所有可用的数据源
    - 智能优先级调度
    - 平台专属数据聚合
    """
    
    _instance: Optional['DataSourceManagerV2'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._sources: Dict[str, DataSource] = {}
        self._cache = TopicCache()
        
        # 注册所有数据源
        self._register_all_sources()
    
    def _register_all_sources(self):
        """注册所有数据源"""
        sources_to_register = [
            # 1. 内置数据源（兜底）
            ("builtin", BuiltinDataSource()),
            
            # 2. 平台专属聚合源（优先）
            ("xiaohongshu", XiaohongshuDataSource()),
            ("douyin", DouyinDataSource()),
            ("weibo", WeiboDataSource()),
            ("zhihu", ZhihuDataSource()),
            ("bilibili", BilibiliDataSource()),
            
            # 3. 付费数据源
            ("shunwei", ShunWeiDataSource()),
            ("qqlykm", QQLYKMDataSource()),
            ("tophub", TopHubDataSource()),
            
            # 4. TIKHUB（需要企业资质）
            ("tikhub", TikHubDataSource()),
            
            # 5. 免费通用源
            ("dailyhot", DailyHotDataSource()),
            ("vvhan", VVhanDataSource()),
            ("weibo_free", WeiboHotDataSource()),
            ("douyin_free", DouyinHotDataSource()),
        ]
        
        for source_id, source in sources_to_register:
            self._sources[source_id] = source
        
        # 统计
        available_count = sum(1 for s in self._sources.values() if s.is_available())
        logger.info(f"[DataSourceManagerV2] Registered {len(self._sources)} sources, {available_count} available")
    
    def get_source(self, source_id: str) -> Optional[DataSource]:
        """获取指定数据源"""
        return self._sources.get(source_id)
    
    def list_sources(self) -> List[Dict[str, Any]]:
        """列出所有数据源"""
        return [s.to_dict() for s in self._sources.values()]
    
    def list_available_sources(self) -> List[str]:
        """列出可用的数据源"""
        return [s_id for s_id, s in self._sources.items() if s.is_available()]
    
    async def fetch_from_platform(
        self,
        platform: str,
        ip_profile: Dict[str, Any],
        limit: int = 10
    ) -> List[TopicData]:
        """
        从指定平台获取数据
        
        Args:
            platform: 平台名称 (xiaohongshu/douyin/weibo/zhihu/bilibili)
            ip_profile: IP画像
            limit: 数量
        """
        source = self._sources.get(platform)
        if not source:
            logger.warning(f"[DataSourceManagerV2] Platform {platform} not found")
            return []
        
        if not source.is_available():
            logger.warning(f"[DataSourceManagerV2] Platform {platform} not available")
            return []
        
        try:
            return await source.fetch(ip_profile, limit)
        except Exception as e:
            logger.error(f"[DataSourceManagerV2] Failed to fetch from {platform}: {e}")
            return []
    
    async def fetch_all_platforms(
        self,
        ip_profile: Dict[str, Any],
        platforms: Optional[List[str]] = None,
        limit_per_platform: int = 5
    ) -> Dict[str, List[TopicData]]:
        """
        从多个平台获取数据
        
        Args:
            ip_profile: IP画像
            platforms: 平台列表，None表示所有
            limit_per_platform: 每个平台数量
        """
        if platforms is None:
            platforms = ["xiaohongshu", "douyin", "weibo", "zhihu", "bilibili"]
        
        results = {}
        
        for platform in platforms:
            topics = await self.fetch_from_platform(platform, ip_profile, limit_per_platform)
            if topics:
                results[platform] = topics
        
        return results
    
    async def fetch_with_strategy(
        self,
        ip_profile: Dict[str, Any],
        limit: int = 12,
        strategy: str = "smart"
    ) -> List[TopicData]:
        """
        使用策略获取数据
        
        Args:
            ip_profile: IP画像
            limit: 总数量
            strategy: 策略
                - smart: 智能策略（优先平台专属源）
                - free_only: 只使用免费源
                - paid_first: 优先付费源
                - platform: 按平台聚合
        """
        if strategy == "smart":
            return await self._strategy_smart(ip_profile, limit)
        elif strategy == "free_only":
            return await self._strategy_free_only(ip_profile, limit)
        elif strategy == "paid_first":
            return await self._strategy_paid_first(ip_profile, limit)
        elif strategy == "platform":
            return await self._strategy_platform(ip_profile, limit)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    async def _strategy_smart(
        self,
        ip_profile: Dict[str, Any],
        limit: int
    ) -> List[TopicData]:
        """智能策略：优先平台专属源，然后付费，最后免费"""
        all_topics = []
        
        # 1. 尝试平台专属源（小红书、抖音优先）
        for platform in ["xiaohongshu", "douyin", "weibo"]:
            if len(all_topics) >= limit:
                break
            
            topics = await self.fetch_from_platform(
                platform, ip_profile, limit - len(all_topics)
            )
            all_topics.extend(topics)
        
        # 2. 如果不足，尝试付费源
        if len(all_topics) < limit:
            paid_sources = ["shunwei", "qqlykm", "tophub"]
            for source_id in paid_sources:
                if len(all_topics) >= limit:
                    break
                
                source = self._sources.get(source_id)
                if not source or not source.is_available():
                    continue
                
                try:
                    topics = await source.fetch(ip_profile, limit - len(all_topics))
                    all_topics.extend(topics)
                except Exception as e:
                    logger.warning(f"[Smart] Paid source {source_id} failed: {e}")
        
        # 3. 最后使用免费源
        if len(all_topics) < limit:
            free_sources = ["dailyhot", "vvhan"]
            for source_id in free_sources:
                if len(all_topics) >= limit:
                    break
                
                source = self._sources.get(source_id)
                if not source or not source.is_available():
                    continue
                
                try:
                    topics = await source.fetch(ip_profile, limit - len(all_topics))
                    all_topics.extend(topics)
                except Exception as e:
                    logger.warning(f"[Smart] Free source {source_id} failed: {e}")
        
        # 4. 兜底
        if len(all_topics) < limit:
            builtin = self._sources.get("builtin")
            if builtin and builtin.is_available():
                topics = await builtin.fetch(ip_profile, limit - len(all_topics))
                all_topics.extend(topics)
        
        return all_topics[:limit]
    
    async def _strategy_free_only(
        self,
        ip_profile: Dict[str, Any],
        limit: int
    ) -> List[TopicData]:
        """只使用免费源"""
        all_topics = []
        
        free_sources = ["dailyhot", "vvhan", "weibo_free", "douyin_free", "builtin"]
        
        for source_id in free_sources:
            if len(all_topics) >= limit:
                break
            
            source = self._sources.get(source_id)
            if not source or not source.is_available():
                continue
            
            try:
                topics = await source.fetch(ip_profile, limit - len(all_topics))
                all_topics.extend(topics)
            except Exception as e:
                logger.warning(f"[FreeOnly] Source {source_id} failed: {e}")
        
        return all_topics[:limit]
    
    async def _strategy_paid_first(
        self,
        ip_profile: Dict[str, Any],
        limit: int
    ) -> List[TopicData]:
        """优先付费源"""
        all_topics = []
        
        paid_sources = ["tikhub", "shunwei", "qqlykm", "tophub"]
        
        for source_id in paid_sources:
            if len(all_topics) >= limit:
                break
            
            source = self._sources.get(source_id)
            if not source or not source.is_available():
                continue
            
            try:
                topics = await source.fetch(ip_profile, limit - len(all_topics))
                all_topics.extend(topics)
            except Exception as e:
                logger.warning(f"[PaidFirst] Source {source_id} failed: {e}")
        
        # 兜底
        if len(all_topics) < limit:
            builtin = self._sources.get("builtin")
            if builtin and builtin.is_available():
                topics = await builtin.fetch(ip_profile, limit - len(all_topics))
                all_topics.extend(topics)
        
        return all_topics[:limit]
    
    async def _strategy_platform(
        self,
        ip_profile: Dict[str, Any],
        limit: int
    ) -> List[TopicData]:
        """按平台聚合策略"""
        # 从每个主要平台获取一些
        platform_limits = {
            "xiaohongshu": max(1, limit // 3),
            "douyin": max(1, limit // 3),
            "weibo": max(1, limit // 6),
            "zhihu": max(1, limit // 6),
        }
        
        all_topics = []
        
        for platform, plimit in platform_limits.items():
            topics = await self.fetch_from_platform(platform, ip_profile, plimit)
            all_topics.extend(topics)
        
        return all_topics[:limit]
    
    def get_data_source_guide(self) -> Dict[str, Any]:
        """获取数据源配置指南"""
        return {
            "免费/开源数据源": {
                "dailyhot": {
                    "name": "DailyHot API",
                    "description": "开源热榜聚合，支持54个平台",
                    "setup": "自部署或找公共实例",
                    "cost": "免费",
                    "env_vars": ["DAILYHOT_API_URL"],
                    "priority": "推荐",
                },
                "vvhan": {
                    "name": "VVhan热榜",
                    "description": "免费热榜聚合API",
                    "setup": "直接使用",
                    "cost": "免费",
                    "env_vars": [],
                    "priority": "推荐",
                },
                "weibo_free": {
                    "name": "微博热搜免费API",
                    "description": "微博热搜",
                    "setup": "直接使用",
                    "cost": "免费",
                    "env_vars": [],
                    "priority": "备选",
                },
            },
            "付费但开发者可获取": {
                "shunwei": {
                    "name": "顺为数据",
                    "description": "小红书/抖音热点",
                    "setup": "注册购买，10元/月",
                    "cost": "10元/月",
                    "env_vars": ["SHUNWEI_API_KEY"],
                    "url": "https://api.itapi.cn",
                    "priority": "推荐（小红书优先）",
                },
                "qqlykm": {
                    "name": "QQ来客源",
                    "description": "多平台热榜",
                    "setup": "注册购买，10元/3000次",
                    "cost": "10元/3000次",
                    "env_vars": ["QQLYKM_API_KEY"],
                    "url": "https://qqlykm.cn",
                    "priority": "推荐",
                },
                "tophub": {
                    "name": "今日热榜官方",
                    "description": "多平台热榜",
                    "setup": "注册获取API Key",
                    "cost": "免费+付费",
                    "env_vars": ["TOPHUB_API_KEY"],
                    "url": "https://www.tophubdata.com",
                    "priority": "推荐",
                },
            },
            "需要企业资质": {
                "tikhub": {
                    "name": "TIKHUB",
                    "description": "专业社交媒体数据",
                    "setup": "企业认证",
                    "cost": "较贵",
                    "env_vars": ["TIKHUB_API_KEY"],
                    "priority": "有能力再考虑",
                },
            },
        }


# 便捷函数
_manager_v2: Optional[DataSourceManagerV2] = None


def get_datasource_manager_v2() -> DataSourceManagerV2:
    """获取数据源管理器V2实例"""
    global _manager_v2
    if _manager_v2 is None:
        _manager_v2 = DataSourceManagerV2()
    return _manager_v2


async def fetch_topics_v2(
    ip_profile: Dict[str, Any],
    limit: int = 12,
    strategy: str = "smart"
) -> List[TopicData]:
    """便捷函数：获取话题 V2"""
    manager = get_datasource_manager_v2()
    return await manager.fetch_with_strategy(ip_profile, limit, strategy)
