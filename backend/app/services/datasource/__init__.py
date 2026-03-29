"""
数据源层 - 统一抽象与多源融合

架构设计：
1. 抽象基类 DataSource - 统一接口
2. 多源优先级队列 - 按优先级获取数据
3. 混合融合策略 - 多源数据智能合并
4. 本地缓存层 - 解耦外部依赖
5. 健康检查机制 - 自动故障转移

使用示例：
    from app.services.datasource import get_datasource_manager, fetch_topics
    
    # 方式1：使用管理器
    manager = get_datasource_manager()
    topics = await manager.fetch_topics(ip_profile, limit=12)
    
    # 方式2：便捷函数
    topics = await fetch_topics(ip_profile, limit=12)
"""

from .base import (
    DataSource, 
    DataSourceConfig, 
    DataSourceHealth,
    DataSourcePriority,
    DataSourceStatus,
    TopicData,
)
from .manager import DataSourceManager, get_datasource_manager, fetch_topics
from .manager_v2 import DataSourceManagerV2, get_datasource_manager_v2, fetch_topics_v2
from .cache import TopicCache
from .builtin_source import BuiltinDataSource
from .tikhub_source import TikHubDataSource
from .competitor_source import CompetitorTopicDataSource
from .multi_source_hotlist import (
    MultiSourceHotlistAggregator,
    fetch_multi_source_hotlist,
    fetch_hotlist_fallback,
    get_multi_source_aggregator,
)
from .builtin_viral_repository import (
    BuiltinViralRepository,
    get_builtin_repository,
    get_builtin_topics,
)

__all__ = [
    # 基类
    "DataSource",
    "DataSourceConfig", 
    "DataSourceHealth",
    "DataSourcePriority",
    "DataSourceStatus",
    "TopicData",
    # 管理器 V1
    "DataSourceManager",
    "get_datasource_manager",
    "fetch_topics",
    # 管理器 V2
    "DataSourceManagerV2",
    "get_datasource_manager_v2",
    "fetch_topics_v2",
    # 缓存
    "TopicCache",
    # 具体实现
    "BuiltinDataSource",
    "TikHubDataSource",
    "CompetitorTopicDataSource",
    # 新增：多源热榜
    "MultiSourceHotlistAggregator",
    "fetch_multi_source_hotlist",
    "fetch_hotlist_fallback",
    "get_multi_source_aggregator",
    # 新增：内置爆款库
    "BuiltinViralRepository",
    "get_builtin_repository",
    "get_builtin_topics",
]
