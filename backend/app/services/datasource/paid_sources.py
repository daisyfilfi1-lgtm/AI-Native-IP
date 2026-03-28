"""
付费但开发者可获取的数据源

包含：
1. 顺为数据 (api.itapi.cn) - 小红书/抖音热点，10元/月
2. QQ来客源 (qqlykm.cn) - 热榜聚合，10元/3000次
3. 今日热榜官方 (tophubdata.com) - 多平台热榜
4. 阿里云市场数据源
"""

import logging
from typing import List, Dict, Any, Optional
import httpx
import os

from .base import DataSource, DataSourceConfig, TopicData, DataSourcePriority

logger = logging.getLogger(__name__)


class ShunWeiDataSource(DataSource):
    """
    顺为数据 (api.itapi.cn)
    
    官网: https://api.itapi.cn/
    价格: 10元/月，3000次/天（小红书热点）
    支持: 小红书、抖音、微博等多平台
    获取: 个人开发者可注册购买
    
    环境变量配置:
    - SHUNWEI_API_KEY: API密钥
    """
    
    BASE_URL = "https://api.itapi.cn"
    
    # API端点映射
    ENDPOINTS = {
        "xiaohongshu": "/api/hotnews/xiaohongshu",  # 小红书热点
        "douyin": "/api/hotnews/douyin",            # 抖音热点
        "weibo": "/api/hotnews/weibo",              # 微博热点
        "zhihu": "/api/hotnews/zhihu",              # 知乎热榜
    }
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="shunwei",
            name="顺为数据（付费）",
            priority=DataSourcePriority.P0,
            enabled=True,
            timeout=10,
            max_results=20,
            cache_ttl=600,  # 10分钟缓存（付费API要节约）
        )
        super().__init__(config)
        
        self.api_key = os.environ.get("SHUNWEI_API_KEY", "")
        self.platforms = os.environ.get("SHUNWEI_PLATFORMS", "xiaohongshu,douyin").split(",")
    
    def is_available(self) -> bool:
        """检查是否配置了API Key"""
        return bool(self.api_key)
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """获取顺为数据"""
        if not self.api_key:
            raise Exception("SHUNWEI_API_KEY not configured")
        
        all_topics = []
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            for platform in self.platforms:
                if len(all_topics) >= limit:
                    break
                
                try:
                    topics = await self._fetch_platform(client, platform, limit // len(self.platforms) + 2)
                    all_topics.extend(topics)
                except Exception as e:
                    logger.warning(f"[ShunWei] Failed to fetch {platform}: {e}")
                    continue
        
        return all_topics[:limit]
    
    async def _fetch_platform(
        self, 
        client: httpx.AsyncClient, 
        platform: str, 
        limit: int
    ) -> List[TopicData]:
        """获取指定平台数据"""
        endpoint = self.ENDPOINTS.get(platform)
        if not endpoint:
            return []
        
        url = f"{self.BASE_URL}{endpoint}"
        params = {"key": self.api_key}
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get("code") != 200:
            raise Exception(f"API error: {data.get('msg', 'unknown')}")
        
        items = data.get("data", [])
        topics = []
        
        for i, item in enumerate(items[:limit]):
            topic = TopicData(
                id=f"shunwei_{platform}_{i}",
                title=item.get("name", ""),
                original_title=item.get("name", ""),
                platform=platform,
                url=item.get("url", ""),
                tags=[platform, "热榜"],
                score=self._calculate_score(item, i),
                source="shunwei",
                extra={
                    "hot_value": item.get("viewnum", ""),
                    "icon": item.get("icon", ""),
                }
            )
            topics.append(topic)
        
        logger.info(f"[ShunWei] Fetched {len(topics)} topics from {platform}")
        return topics
    
    def _calculate_score(self, item: Dict, rank: int) -> float:
        """计算分数"""
        base = 4.2
        rank_bonus = max(0, 0.6 - rank * 0.05)
        
        # 热度加成
        hot_str = str(item.get("viewnum", "0"))
        if "万" in hot_str or "w" in hot_str.lower():
            hot_bonus = 0.2
        elif "亿" in hot_str:
            hot_bonus = 0.3
        else:
            hot_bonus = 0
        
        return min(5.0, base + rank_bonus + hot_bonus)


class QQLYKMDataSource(DataSource):
    """
    QQ来客源 (qqlykm.cn)
    
    官网: https://qqlykm.cn/
    价格: 10元/3000次，30元/10000次
    支持: 微博、知乎、抖音、小红书等多平台热榜
    获取: 个人开发者可注册购买
    
    环境变量配置:
    - QQLYKM_API_KEY: API密钥
    """
    
    BASE_URL = "https://qqlykm.cn/api/hotlist/get"
    
    # 平台类型映射
    PLATFORM_TYPES = {
        "weibo": "weibo",           # 微博
        "zhihu": "zhihu",           # 知乎
        "douyin": "douyin",         # 抖音
        "xiaohongshu": "xiaohongshu",  # 小红书
        "bilibili": "bilibili",     # B站
        "baidu": "baidu",           # 百度
        "toutiao": "toutiao",       # 头条
        "kuaishou": "kuaishou",     # 快手
    }
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="qqlykm",
            name="QQ来客源（付费）",
            priority=DataSourcePriority.P0,
            enabled=True,
            timeout=10,
            max_results=20,
            cache_ttl=600,
        )
        super().__init__(config)
        
        self.api_key = os.environ.get("QQLYKM_API_KEY", "")
        self.types = os.environ.get("QQLYKM_TYPES", "xiaohongshu,douyin,weibo,zhihu").split(",")
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """获取QQ来客源数据"""
        if not self.api_key:
            raise Exception("QQLYKM_API_KEY not configured")
        
        all_topics = []
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            for type_key in self.types:
                if len(all_topics) >= limit:
                    break
                
                try:
                    topics = await self._fetch_type(client, type_key, limit // len(self.types) + 2)
                    all_topics.extend(topics)
                except Exception as e:
                    logger.warning(f"[QQLYKM] Failed to fetch {type_key}: {e}")
                    continue
        
        return all_topics[:limit]
    
    async def _fetch_type(
        self, 
        client: httpx.AsyncClient, 
        type_key: str, 
        limit: int
    ) -> List[TopicData]:
        """获取指定类型数据"""
        params = {
            "key": self.api_key,
            "type": type_key,
        }
        
        response = await client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get("code") != 200:
            raise Exception(f"API error: {data.get('msg', 'unknown')}")
        
        items = data.get("data", [])
        topics = []
        
        for i, item in enumerate(items[:limit]):
            topic = TopicData(
                id=f"qqlykm_{type_key}_{i}",
                title=item.get("title", ""),
                original_title=item.get("title", ""),
                platform=type_key,
                url=item.get("url", ""),
                tags=[type_key, "热榜"],
                score=4.5 - i * 0.05,
                source="qqlykm",
                extra={
                    "hot": item.get("hot", ""),
                    "desc": item.get("desc", ""),
                }
            )
            topics.append(topic)
        
        logger.info(f"[QQLYKM] Fetched {len(topics)} topics from {type_key}")
        return topics


class TopHubDataSource(DataSource):
    """
    今日热榜官方 API (tophubdata.com)
    
    官网: https://www.tophubdata.com/
    价格: 
    - 快照列表: 免费
    - 详细内容: 1u/个快照（约0.1元）
    支持: 微信、今日头条、百度、知乎、V2EX、微博、贴吧、豆瓣、虎扑、Github、抖音等
    
    特点:
    - 官方热榜聚合平台
    - 数据质量高
    - 有免费额度
    
    环境变量配置:
    - TOPHUB_API_KEY: API密钥
    """
    
    BASE_URL = "https://api.tophubdata.com"
    
    # 常用节点ID（需要申请）
    DEFAULT_NODES = [
        "mproPpoq6O",  # 微博
        "WnBe01o371",  # 知乎
        "KbEMD7K6Ow",  # 抖音
        "5VaobgvAj1",  # 小红书（需要确认）
    ]
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="tophub",
            name="今日热榜官方（免费+付费）",
            priority=DataSourcePriority.P1,
            enabled=True,
            timeout=10,
            max_results=20,
            cache_ttl=1800,
        )
        super().__init__(config)
        
        self.api_key = os.environ.get("TOPHUB_API_KEY", "")
        self.nodes = os.environ.get("TOPHUB_NODES", ",".join(self.DEFAULT_NODES)).split(",")
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """获取今日热榜数据"""
        if not self.api_key:
            raise Exception("TOPHUB_API_KEY not configured")
        
        all_topics = []
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            for node_id in self.nodes:
                if len(all_topics) >= limit:
                    break
                
                try:
                    topics = await self._fetch_node(client, node_id, limit // len(self.nodes) + 2)
                    all_topics.extend(topics)
                except Exception as e:
                    logger.warning(f"[TopHub] Failed to fetch node {node_id}: {e}")
                    continue
        
        return all_topics[:limit]
    
    async def _fetch_node(
        self, 
        client: httpx.AsyncClient, 
        node_id: str, 
        limit: int
    ) -> List[TopicData]:
        """获取指定节点数据（免费快照列表）"""
        url = f"{self.BASE_URL}/nodes/{node_id}/snapshots"
        headers = {"Authorization": self.api_key}
        params = {"details": 0}  # 免费模式，仅获取列表
        
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        if data.get("code") != 200:
            raise Exception(f"API error: {data.get('msg', 'unknown')}")
        
        items = data.get("data", [])
        topics = []
        
        for i, item in enumerate(items[:limit]):
            # 快照列表只有基本信息，没有详细内容
            # 如果需要详细内容，需要额外调用（收费）
            topic = TopicData(
                id=f"tophub_{node_id}_{i}",
                title=item.get("title", ""),
                original_title=item.get("title", ""),
                platform=node_id,
                url=item.get("url", ""),
                tags=["热榜"],
                score=4.0,
                source="tophub",
                extra={
                    "snapshot_id": item.get("id"),
                    "node_id": node_id,
                }
            )
            topics.append(topic)
        
        logger.info(f"[TopHub] Fetched {len(topics)} topics from node {node_id}")
        return topics


class AlibabaCloudDataSource(DataSource):
    """
    阿里云市场数据源
    
    阿里云市场有大量数据API，可按需购买
    优点: 稳定、有SLA、文档完善
    价格: 各供应商不同，一般10-100元/月
    
    推荐API:
    - 微博热搜API
    - 抖音热搜API
    - 小红书数据API
    
    环境变量配置:
    - ALIBABA_CLOUD_APP_CODE: 阿里云AppCode
    - ALIBABA_CLOUD_API_ENDPOINT: API端点
    """
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="alibaba_cloud",
            name="阿里云市场（付费）",
            priority=DataSourcePriority.P0,
            enabled=False,  # 默认不启用，需要手动配置
            timeout=10,
            max_results=20,
            cache_ttl=600,
        )
        super().__init__(config)
        
        self.app_code = os.environ.get("ALIBABA_CLOUD_APP_CODE", "")
        self.endpoint = os.environ.get("ALIBABA_CLOUD_API_ENDPOINT", "")
    
    def is_available(self) -> bool:
        return bool(self.app_code and self.endpoint)
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """获取阿里云市场数据"""
        if not self.is_available():
            raise Exception("Alibaba Cloud not configured")
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            headers = {"Authorization": f"APPCODE {self.app_code}"}
            response = await client.get(self.endpoint, headers=headers)
            response.raise_for_status()
            
            # 解析取决于具体API
            data = response.json()
            
            # TODO: 根据实际API格式解析
            logger.info(f"[AlibabaCloud] Fetched data: {len(str(data))} chars")
            return []
