"""
数据源抽象基类
定义所有数据源的统一接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DataSourcePriority(Enum):
    """数据源优先级"""
    P0 = 0   # 最高 - 竞品监控、精准数据源
    P1 = 1   # 高 - 关键词搜索、话题标签
    P2 = 2   # 中 - 热榜聚合
    P3 = 3   # 低 - 内置库兜底


class DataSourceStatus(Enum):
    """数据源状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # 可用但响应慢
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


@dataclass
class DataSourceConfig:
    """数据源配置"""
    source_id: str                          # 唯一标识
    name: str                               # 显示名称
    priority: DataSourcePriority           # 优先级
    enabled: bool = True                   # 是否启用
    timeout: int = 10                      # 超时时间(秒)
    max_results: int = 20                  # 最大返回数
    cache_ttl: int = 3600                  # 缓存时间(秒)
    fallback_sources: List[str] = field(default_factory=list)  # 降级数据源
    config: Dict[str, Any] = field(default_factory=dict)       # 专属配置


@dataclass
class DataSourceHealth:
    """数据源健康状态"""
    source_id: str
    status: DataSourceStatus
    last_check: datetime
    response_time_ms: float
    success_rate: float       # 最近1小时成功率
    error_count: int
    last_error: Optional[str]
    
    @property
    def is_healthy(self) -> bool:
        return self.status == DataSourceStatus.HEALTHY


@dataclass
class TopicData:
    """标准化话题数据格式"""
    id: str
    title: str
    original_title: str
    platform: str           # douyin/xiaohongshu/kuaishou/builtin
    url: str
    tags: List[str]
    score: float           # 0-5分
    likes: int = 0
    comments: int = 0
    shares: int = 0
    author_followers: int = 0
    publish_time: Optional[datetime] = None
    source: str = ""       # 原始数据源
    extra: Dict[str, Any] = field(default_factory=dict)


class DataSource(ABC):
    """
    数据源抽象基类
    
    所有具体数据源必须实现此接口
    """
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.health = DataSourceHealth(
            source_id=config.source_id,
            status=DataSourceStatus.HEALTHY,
            last_check=datetime.now(),
            response_time_ms=0,
            success_rate=1.0,
            error_count=0,
            last_error=None
        )
    
    @property
    def source_id(self) -> str:
        return self.config.source_id
    
    @property
    def priority(self) -> int:
        return self.config.priority.value
    
    @abstractmethod
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """
        获取话题数据
        
        Args:
            ip_profile: IP画像
            limit: 获取数量
            
        Returns:
            话题列表
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        pass
    
    async def fetch_with_fallback(
        self, 
        ip_profile: Dict[str, Any], 
        limit: int,
        fallback_chain: List['DataSource']
    ) -> List[TopicData]:
        """
        带降级链的获取
        
        如果当前数据源失败，按fallback_chain顺序尝试
        """
        try:
            results = await self.fetch(ip_profile, limit)
            if results:
                return results
        except Exception as e:
            logger.warning(f"[{self.source_id}] fetch failed: {e}")
            self._record_error(str(e))
        
        # 尝试降级数据源
        for fallback in fallback_chain:
            try:
                logger.info(f"[{self.source_id}] falling back to {fallback.source_id}")
                results = await fallback.fetch(ip_profile, limit)
                if results:
                    return results
            except Exception as e:
                logger.warning(f"[{fallback.source_id}] fallback failed: {e}")
                continue
        
        return []
    
    def _record_error(self, error: str):
        """记录错误"""
        self.health.error_count += 1
        self.health.last_error = error
        self.health.last_check = datetime.now()
        
        # 更新状态
        if self.health.error_count > 5:
            self.health.status = DataSourceStatus.UNAVAILABLE
        elif self.health.error_count > 2:
            self.health.status = DataSourceStatus.DEGRADED
    
    def _record_success(self, response_time_ms: float):
        """记录成功"""
        self.health.response_time_ms = response_time_ms
        self.health.last_check = datetime.now()
        self.health.success_rate = min(1.0, self.health.success_rate * 0.9 + 0.1)
        
        if self.health.success_rate > 0.8:
            self.health.status = DataSourceStatus.HEALTHY
            self.health.error_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_id": self.source_id,
            "name": self.config.name,
            "priority": self.priority,
            "enabled": self.config.enabled,
            "status": self.health.status.value,
            "health": {
                "success_rate": self.health.success_rate,
                "response_time_ms": self.health.response_time_ms,
                "error_count": self.health.error_count,
                "last_error": self.health.last_error,
            }
        }
