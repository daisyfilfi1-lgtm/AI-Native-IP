"""
免费/开源数据源实现

包含：
1. DailyHot API - 开源热榜聚合，支持54个平台
2. VVhan热榜API - 免费热榜聚合
3. 微博热搜API - 免费微博热搜
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx

from .base import DataSource, DataSourceConfig, TopicData, DataSourcePriority

logger = logging.getLogger(__name__)


class DailyHotDataSource(DataSource):
    """
    DailyHot API 数据源（开源/自部署）
    
    项目地址: https://github.com/imsyy/DailyHotApi
    支持平台: 微博、知乎、抖音、B站、小红书等54个平台
    
    部署方式:
    1. Vercel一键部署（免费）
    2. Docker本地部署
    3. 使用公共API（可能不稳定）
    
    获取方式:
    - 自己部署: https://github.com/imsyy/DailyHotApi
    - 或者使用已部署的实例
    """
    
    # 支持的平台映射
    PLATFORM_MAP = {
        "xiaohongshu": {"name": "小红书", "type": "lifestyle"},
        "douyin": {"name": "抖音", "type": "video"},
        "weibo": {"name": "微博", "type": "social"},
        "zhihu": {"name": "知乎", "type": "qa"},
        "bilibili": {"name": "B站", "type": "video"},
        "kuaishou": {"name": "快手", "type": "video"},
        "baidu": {"name": "百度", "type": "search"},
    }
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Args:
            base_url: DailyHot API地址，默认使用公共实例或配置
        """
        config = DataSourceConfig(
            source_id="dailyhot",
            name="DailyHot热榜（开源）",
            priority=DataSourcePriority.P1,
            enabled=True,
            timeout=10,
            max_results=20,
            cache_ttl=1800,
        )
        super().__init__(config)
        
        # 优先使用传入的URL，其次环境变量，最后默认公共实例
        import os
        self.base_url = base_url or os.environ.get("DAILYHOT_API_URL", "https://api-hot.imsyy.top")
        self.platforms = os.environ.get("DAILYHOT_PLATFORMS", "xiaohongshu,douyin,weibo,zhihu,bilibili").split(",")
    
    def is_available(self) -> bool:
        """检查API是否可用"""
        return bool(self.base_url)
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """
        从DailyHot获取热榜数据
        
        从配置的平台获取热榜数据
        """
        all_topics = []
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            for platform in self.platforms:
                if len(all_topics) >= limit:
                    break
                
                try:
                    topics = await self._fetch_platform(client, platform, limit // len(self.platforms) + 2)
                    all_topics.extend(topics)
                except Exception as e:
                    logger.warning(f"[DailyHot] Failed to fetch {platform}: {e}")
                    continue
        
        return all_topics[:limit]
    
    async def _fetch_platform(
        self, 
        client: httpx.AsyncClient, 
        platform: str, 
        limit: int
    ) -> List[TopicData]:
        """获取指定平台的热榜"""
        url = f"{self.base_url}/{platform}"
        
        response = await client.get(url)
        response.raise_for_status()
        
        data = response.json()
        if not data.get("success"):
            raise Exception(f"API error: {data.get('message', 'unknown')}")
        
        items = data.get("data", [])
        platform_info = self.PLATFORM_MAP.get(platform, {"name": platform, "type": "other"})
        
        topics = []
        for i, item in enumerate(items[:limit]):
            topic = TopicData(
                id=f"dailyhot_{platform}_{i}",
                title=item.get("title", ""),
                original_title=item.get("title", ""),
                platform=platform,
                url=item.get("url", ""),
                tags=[platform_info["name"], "热榜"],
                score=self._calculate_score(item, i),
                source="dailyhot",
                extra={
                    "platform_name": platform_info["name"],
                    "hot_value": item.get("hot", ""),
                }
            )
            topics.append(topic)
        
        logger.info(f"[DailyHot] Fetched {len(topics)} topics from {platform}")
        return topics
    
    def _calculate_score(self, item: Dict, rank: int) -> float:
        """根据热度和排名计算分数"""
        base_score = 4.0
        
        # 排名越高分数越高
        rank_bonus = max(0, 0.5 - rank * 0.05)
        
        # 如果有热度值，解析热度
        hot_str = str(item.get("hot", "0"))
        if "万" in hot_str:
            try:
                hot_num = float(hot_str.replace("万", ""))
                hot_bonus = min(0.5, hot_num / 100)  # 最高加0.5
            except:
                hot_bonus = 0
        else:
            hot_bonus = 0
        
        return min(5.0, base_score + rank_bonus + hot_bonus)


class VVhanDataSource(DataSource):
    """
    VVhan热榜API（免费）
    
    地址: https://api.vvhan.com/api/hotlist/all
    支持: 微博、今日头条、知乎、虎扑、36氪、B站、抖音等
    费用: 完全免费
    限制: 无明确限制（请合理使用）
    """
    
    API_URL = "https://api.vvhan.com/api/hotlist/all"
    
    # IP相关度权重（用于排序）
    PLATFORM_RELEVANCE = {
        "douyin": 1.0,      # 抖音 - 短视频
        "xiaohongshu": 1.0,  # 小红书 - 生活方式
        "weibo": 0.8,       # 微博 - 社交媒体
        "kuaizixun": 0.7,   # 快资讯
        "baidu": 0.6,       # 百度
        "zhihu": 0.6,       # 知乎
        "bilibili": 0.5,    # B站
    }
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="vvhan",
            name="VVhan热榜（免费）",
            priority=DataSourcePriority.P1,
            enabled=True,
            timeout=10,
            max_results=30,
            cache_ttl=1800,
        )
        super().__init__(config)
    
    def is_available(self) -> bool:
        """始终可用"""
        return True
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """获取VVhan热榜数据"""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                response = await client.get(self.API_URL)
                response.raise_for_status()
                
                data = response.json()
                if not data.get("success"):
                    raise Exception(f"API error: {data.get('message', 'unknown')}")
                
                return self._parse_response(data.get("data", []), limit)
                
            except Exception as e:
                logger.error(f"[VVhan] API request failed: {e}")
                raise
    
    def _parse_response(self, platform_data: List[Dict], limit: int) -> List[TopicData]:
        """解析API响应"""
        all_topics = []
        
        for platform_item in platform_data:
            platform_name = platform_item.get("name", "")
            platform_key = self._get_platform_key(platform_name)
            
            items = platform_item.get("data", [])
            relevance = self.PLATFORM_RELEVANCE.get(platform_key, 0.3)
            
            for i, item in enumerate(items[:5]):  # 每个平台取前5条
                topic = TopicData(
                    id=f"vvhan_{platform_key}_{i}",
                    title=item.get("title", ""),
                    original_title=item.get("title", ""),
                    platform=platform_key,
                    url=item.get("url", ""),
                    tags=[platform_name, "热榜"],
                    score=self._calculate_score(item, i, relevance),
                    source="vvhan",
                    extra={
                        "platform_name": platform_name,
                        "relevance": relevance,
                    }
                )
                all_topics.append(topic)
        
        # 按相关度和分数排序
        all_topics.sort(key=lambda x: x.score * x.extra.get("relevance", 0.5), reverse=True)
        
        logger.info(f"[VVhan] Fetched {len(all_topics)} topics")
        return all_topics[:limit]
    
    def _get_platform_key(self, name: str) -> str:
        """从名称获取平台key"""
        name_map = {
            "微博": "weibo",
            "抖音": "douyin",
            "知乎": "zhihu",
            "哔哩哔哩": "bilibili",
            "B站": "bilibili",
            "百度": "baidu",
        }
        return name_map.get(name, name.lower().replace(" ", ""))
    
    def _calculate_score(self, item: Dict, rank: int, relevance: float) -> float:
        """计算分数"""
        base = 4.0
        rank_bonus = max(0, 0.5 - rank * 0.08)
        relevance_bonus = relevance * 0.3
        return min(5.0, base + rank_bonus + relevance_bonus)


class WeiboHotDataSource(DataSource):
    """
    微博热搜API（免费）
    
    地址: https://api.aa1.cn/doc/weibo-rs.html
    费用: 完全免费
    限制: 无明确限制
    """
    
    API_URL = "https://api.aa1.cn/api/weibo-rs/"
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="weibo_free",
            name="微博热搜（免费）",
            priority=DataSourcePriority.P2,
            enabled=True,
            timeout=8,
            max_results=20,
            cache_ttl=1800,
        )
        super().__init__(config)
    
    def is_available(self) -> bool:
        return True
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """获取微博热搜"""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                response = await client.get(self.API_URL)
                response.raise_for_status()
                
                data = response.json()
                if data.get("code") != 200:
                    raise Exception(f"API error: {data.get('msg', 'unknown')}")
                
                items = data.get("data", [])
                topics = []
                
                for i, item in enumerate(items[:limit]):
                    topic = TopicData(
                        id=f"weibo_free_{i}",
                        title=item.get("title", ""),
                        original_title=item.get("title", ""),
                        platform="weibo",
                        url=item.get("url", ""),
                        tags=["微博", "热搜"],
                        score=self._calculate_score(item, i),
                        source="weibo_free",
                        extra={
                            "hot_value": item.get("hot", ""),
                            "label": item.get("label", ""),
                        }
                    )
                    topics.append(topic)
                
                logger.info(f"[WeiboFree] Fetched {len(topics)} topics")
                return topics
                
            except Exception as e:
                logger.error(f"[WeiboFree] API request failed: {e}")
                raise
    
    def _calculate_score(self, item: Dict, rank: int) -> float:
        """计算分数"""
        base = 4.0
        rank_bonus = max(0, 0.5 - rank * 0.04)  # 前10名加分
        
        # 标签加成
        label = item.get("label", "")
        label_bonus = 0.2 if label in ["爆", "热"] else 0
        
        return min(5.0, base + rank_bonus + label_bonus)


class DouyinHotDataSource(DataSource):
    """
    抖音即时热搜榜（免费）
    
    费用: 免费
    注意: 需要找到稳定的API源
    """
    
    # 多个可能的API源
    API_ENDPOINTS = [
        "https://api.aa1.cn/api/douyin-hot/",
        "https://api.vvhan.com/api/hotlist/douyin",
    ]
    
    def __init__(self):
        config = DataSourceConfig(
            source_id="douyin_free",
            name="抖音热搜（免费）",
            priority=DataSourcePriority.P1,
            enabled=True,
            timeout=8,
            max_results=20,
            cache_ttl=1800,
        )
        super().__init__(config)
    
    def is_available(self) -> bool:
        return True
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """尝试从多个端点获取抖音热搜"""
        for endpoint in self.API_ENDPOINTS:
            try:
                topics = await self._try_endpoint(endpoint, limit)
                if topics:
                    return topics
            except Exception as e:
                logger.warning(f"[DouyinFree] Endpoint {endpoint} failed: {e}")
                continue
        
        return []
    
    async def _try_endpoint(self, endpoint: str, limit: int) -> List[TopicData]:
        """尝试单个端点"""
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            
            data = response.json()
            
            # 根据不同端点解析
            if "aa1.cn" in endpoint:
                return self._parse_aa1(data, limit)
            elif "vvhan" in endpoint:
                return self._parse_vvhan(data, limit)
            else:
                return []
    
    def _parse_aa1(self, data: Dict, limit: int) -> List[TopicData]:
        """解析aa1格式"""
        items = data.get("data", [])
        topics = []
        
        for i, item in enumerate(items[:limit]):
            topic = TopicData(
                id=f"douyin_free_{i}",
                title=item.get("title", ""),
                original_title=item.get("title", ""),
                platform="douyin",
                url=item.get("url", ""),
                tags=["抖音", "热搜"],
                score=4.5 - i * 0.05,
                source="douyin_free",
            )
            topics.append(topic)
        
        return topics
    
    def _parse_vvhan(self, data: Dict, limit: int) -> List[TopicData]:
        """解析vvhan格式"""
        if not data.get("success"):
            return []
        
        items = data.get("data", [])
        topics = []
        
        for i, item in enumerate(items[:limit]):
            topic = TopicData(
                id=f"douyin_free_{i}",
                title=item.get("title", ""),
                original_title=item.get("title", ""),
                platform="douyin",
                url=item.get("url", ""),
                tags=["抖音", "热榜"],
                score=4.5 - i * 0.05,
                source="douyin_free",
            )
            topics.append(topic)
        
        return topics
