"""
数据源管理器

核心职责：
1. 管理所有数据源生命周期
2. 多源融合策略
3. 健康检查与故障转移
4. 数据去重与排序
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

from .base import (
    DataSource, DataSourceConfig, TopicData, 
    DataSourcePriority, DataSourceStatus
)
from .cache import TopicCache
from .builtin_source import BuiltinDataSource
from .tikhub_source import TikHubDataSource

logger = logging.getLogger(__name__)


class DataSourceManager:
    """
    数据源管理器
    
    单例模式，统一管理所有数据源
    """
    
    _instance: Optional['DataSourceManager'] = None
    
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
        
        # 注册默认数据源
        self._register_default_sources()
    
    def _register_default_sources(self):
        """注册默认数据源"""
        # 内置数据源 - 始终可用
        self.register(BuiltinDataSource())
        
        # TIKHUB数据源 - 需要配置
        self.register(TikHubDataSource())
        
        logger.info(f"[DataSourceManager] Registered {len(self._sources)} sources")
    
    def register(self, source: DataSource):
        """注册数据源"""
        self._sources[source.source_id] = source
        logger.info(f"[DataSourceManager] Registered source: {source.source_id}")
    
    def unregister(self, source_id: str):
        """注销数据源"""
        if source_id in self._sources:
            del self._sources[source_id]
            logger.info(f"[DataSourceManager] Unregistered source: {source_id}")
    
    def get_source(self, source_id: str) -> Optional[DataSource]:
        """获取指定数据源"""
        return self._sources.get(source_id)
    
    def list_sources(self) -> List[Dict[str, Any]]:
        """列出所有数据源"""
        return [s.to_dict() for s in self._sources.values()]
    
    async def fetch_topics(
        self,
        ip_profile: Dict[str, Any],
        limit: int = 12,
        strategy: str = "hybrid"  # hybrid/priority/parallel
    ) -> List[TopicData]:
        """
        获取话题（多源融合入口）
        
        Args:
            ip_profile: IP画像
            limit: 返回数量
            strategy: 获取策略
                - hybrid: 混合策略（推荐）
                - priority: 按优先级顺序获取
                - parallel: 并行获取所有源
        
        Returns:
            融合后的话题列表
        """
        if strategy == "hybrid":
            return await self._fetch_hybrid(ip_profile, limit)
        elif strategy == "priority":
            return await self._fetch_priority(ip_profile, limit)
        elif strategy == "parallel":
            return await self._fetch_parallel(ip_profile, limit)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    async def _fetch_hybrid(
        self, 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[TopicData]:
        """
        混合策略（推荐）
        
        策略逻辑：
        1. 优先从实时数据源获取（TIKHUB等）
        2. 实时源不足，补充内置库
        3. 内置库优先补充不足的内容类型
        """
        ip_id = ip_profile.get("ip_id", "default")
        result: List[TopicData] = []
        
        # 尝试从实时数据源获取
        for source in self._get_sources_by_priority():
            if not source.is_available():
                continue
            
            try:
                topics = await asyncio.wait_for(
                    source.fetch(ip_profile, limit),
                    timeout=source.config.timeout
                )
                
                if topics:
                    result.extend(topics)
                    logger.info(f"[DataSourceManager] {source.source_id} returned {len(topics)} topics")
                    
                    # 如果已获取足够数据，停止
                    if len(result) >= limit:
                        break
                        
            except asyncio.TimeoutError:
                logger.warning(f"[DataSourceManager] {source.source_id} timeout")
            except Exception as e:
                logger.error(f"[DataSourceManager] {source.source_id} error: {e}")
        
        # 如果实时源不足，用内置库补充
        if len(result) < limit:
            builtin = self._sources.get("builtin")
            if builtin and builtin.is_available():
                needed = limit - len(result)
                builtin_topics = await builtin.fetch(ip_profile, needed)
                
                # 检查内容类型分布，优先补充不足的类型
                result = self._fill_content_matrix(result, builtin_topics, limit)
        
        # 去重
        result = self._deduplicate(result)
        
        return result[:limit]
    
    async def _fetch_priority(
        self, 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[TopicData]:
        """按优先级顺序获取"""
        for source in self._get_sources_by_priority():
            if not source.is_available():
                continue
            
            try:
                topics = await source.fetch(ip_profile, limit)
                if topics:
                    return topics[:limit]
            except Exception as e:
                logger.warning(f"[DataSourceManager] {source.source_id} failed: {e}")
                continue
        
        return []
    
    async def _fetch_parallel(
        self, 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[TopicData]:
        """并行获取所有源"""
        tasks = []
        sources = []
        
        for source in self._sources.values():
            if source.is_available():
                task = asyncio.create_task(
                    self._fetch_with_timeout(source, ip_profile, limit)
                )
                tasks.append(task)
                sources.append(source)
        
        if not tasks:
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_topics = []
        for source, result in zip(sources, results):
            if isinstance(result, Exception):
                logger.warning(f"[DataSourceManager] {source.source_id} failed: {result}")
            elif result:
                all_topics.extend(result)
        
        # 去重
        return self._deduplicate(all_topics)[:limit]
    
    async def _fetch_with_timeout(
        self, 
        source: DataSource, 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[TopicData]:
        """带超时的获取"""
        return await asyncio.wait_for(
            source.fetch(ip_profile, limit),
            timeout=source.config.timeout
        )
    
    def _get_sources_by_priority(self) -> List[DataSource]:
        """按优先级排序获取数据源"""
        return sorted(
            self._sources.values(),
            key=lambda s: s.priority
        )
    
    def _fill_content_matrix(
        self,
        existing: List[TopicData],
        candidates: List[TopicData],
        limit: int
    ) -> List[TopicData]:
        """
        按内容矩阵填充
        
        确保4-3-2-1分布
        """
        # 统计现有分布
        type_counts = {"money": 0, "emotion": 0, "skill": 0, "life": 0}
        for topic in existing:
            ctype = topic.extra.get("content_type", "other")
            if ctype in type_counts:
                type_counts[ctype] += 1
        
        # 目标分布
        target = {
            "money": int(limit * 0.4),
            "emotion": int(limit * 0.3),
            "skill": int(limit * 0.2),
            "life": max(1, limit - int(limit * 0.4) - int(limit * 0.3) - int(limit * 0.2)),
        }
        
        result = list(existing)
        
        # 按缺口补充
        for ctype in ["money", "emotion", "skill", "life"]:
            needed = target[ctype] - type_counts[ctype]
            if needed > 0:
                for topic in candidates:
                    if topic.extra.get("content_type") == ctype:
                        result.append(topic)
                        needed -= 1
                        if needed <= 0:
                            break
        
        # 如果还有空位，任意补充
        if len(result) < limit:
            for topic in candidates:
                if topic not in result:
                    result.append(topic)
                    if len(result) >= limit:
                        break
        
        return result
    
    def _deduplicate(self, topics: List[TopicData]) -> List[TopicData]:
        """去重"""
        seen: Set[str] = set()
        result = []
        
        for topic in topics:
            key = topic.title.lower().strip()
            if key not in seen:
                seen.add(key)
                result.append(topic)
        
        return result
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        results = {}
        
        for source in self._sources.values():
            results[source.source_id] = {
                "available": source.is_available(),
                "health": source.health.to_dict() if hasattr(source.health, 'to_dict') else str(source.health)
            }
        
        return results


# 便捷函数
def get_datasource_manager() -> DataSourceManager:
    """获取数据源管理器实例"""
    return DataSourceManager()


async def fetch_topics(
    ip_profile: Dict[str, Any],
    limit: int = 12,
    strategy: str = "hybrid"
) -> List[TopicData]:
    """便捷函数：获取话题"""
    manager = get_datasource_manager()
    return await manager.fetch_topics(ip_profile, limit, strategy)
