"""
多源热榜聚合服务
聚合抖音、小红书、快手、B站等多个平台的热榜数据
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import random

import httpx

from app.services.tikhub_client import (
    is_configured as tikhub_configured,
    fetch_douyin_high_play_hot_list,
    fetch_douyin_low_fan_hot_list,
    billboard_to_topic_cards,
)
from app.services.datasource.base import TopicData, DataSource

logger = logging.getLogger(__name__)


class PlatformType(Enum):
    """平台类型"""
    DOUYIN = "douyin"
    XIAOHONGSHU = "xiaohongshu"
    KUAISHOU = "kuaishou"
    BILIBILI = "bilibili"
    WEIBO = "weibo"


@dataclass
class HotListItem:
    """热榜条目"""
    title: str
    platform: PlatformType
    url: str = ""
    play_count: int = 0
    like_count: int = 0
    author: str = ""
    hot_score: float = 0.0
    rank: int = 0
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiSourceResult:
    """多源聚合结果"""
    items: List[HotListItem]
    source_stats: Dict[str, int]  # 各来源数量统计
    fetch_time: datetime
    errors: List[str]


class DouyinHotSource:
    """抖音热榜源（TikHub）"""
    
    async def fetch(self, limit: int = 20) -> Tuple[List[HotListItem], str]:
        """
        获取抖音热榜
        
        Returns:
            (items, error_msg)
        """
        if not tikhub_configured():
            return [], "TikHub未配置"
        
        items = []
        error_msg = ""
        
        try:
            # 尝试高播榜
            logger.info("[DouyinHot] Fetching high play list...")
            raw = await fetch_douyin_high_play_hot_list(page=1, page_size=max(limit, 10))
            cards = billboard_to_topic_cards(raw, limit=limit)
            
            if cards:
                for i, card in enumerate(cards):
                    items.append(HotListItem(
                        title=card.get("title", ""),
                        platform=PlatformType.DOUYIN,
                        url=card.get("sourceUrl", ""),
                        play_count=self._parse_play_count(card.get("estimatedViews", "0")),
                        hot_score=card.get("score", 4.5) * 20,  # 转换为百分制
                        rank=i + 1,
                        tags=card.get("tags", ["抖音", "热榜"]),
                        extra={"source": "douyin_high_play", "original_data": card}
                    ))
                return items, ""
            
            # 高播榜为空，尝试低粉爆款榜
            logger.info("[DouyinHot] High play empty, trying low fan list...")
            raw_low = await fetch_douyin_low_fan_hot_list(page=1, page_size=max(limit, 10), date_window=1)
            cards_low = billboard_to_topic_cards(raw_low, limit=limit)
            
            if cards_low:
                for i, card in enumerate(cards_low):
                    items.append(HotListItem(
                        title=card.get("title", ""),
                        platform=PlatformType.DOUYIN,
                        url=card.get("sourceUrl", ""),
                        play_count=self._parse_play_count(card.get("estimatedViews", "0")),
                        hot_score=card.get("score", 4.5) * 20,
                        rank=i + 1,
                        tags=card.get("tags", ["抖音", "低粉爆款"]),
                        extra={"source": "douyin_low_fan", "original_data": card}
                    ))
                return items, ""
            
            error_msg = "抖音热榜返回空数据"
            
        except Exception as e:
            error_msg = f"抖音热榜获取失败: {str(e)}"
            logger.error(f"[DouyinHot] {error_msg}")
        
        return items, error_msg
    
    def _parse_play_count(self, views_str: str) -> int:
        """解析播放量字符串"""
        if not views_str or views_str == "—":
            return 0
        try:
            # 处理 "1.5万", "2.3千" 等格式
            if "万" in views_str:
                num = float(views_str.replace("万", "").replace("+", ""))
                return int(num * 10000)
            elif "千" in views_str:
                num = float(views_str.replace("千", "").replace("+", ""))
                return int(num * 1000)
            else:
                return int(float(views_str.replace(",", "")))
        except:
            return 0


class XiaohongshuHotSource:
    """小红书热榜源"""
    
    # 小红书热门话题API（使用第三方或爬虫）
    XHS_HOT_API = "https://www.xiaohongshu.com/web_api/sns/v1/search/trending"
    
    async def fetch(self, limit: int = 20) -> Tuple[List[HotListItem], str]:
        """获取小红书热榜"""
        items = []
        
        try:
            # 小红书热榜需要通过web scraping或第三方API
            # 这里先使用一个简化的实现，后续可接入Playwright或第三方服务
            logger.info("[XiaohongshuHot] Fetching trending topics...")
            
            # 使用简单的HTTP请求尝试获取
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 尝试获取小红书热门搜索
                headers = {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X)",
                    "Referer": "https://www.xiaohongshu.com/",
                }
                
                # 由于小红书API需要签名，这里使用备用方案
                # 实际部署时可以通过Playwright或接入第三方服务
                logger.warning("[XiaohongshuHot] Using fallback trending list")
                
                # 返回一些预设的小红书热门话题作为示例
                # 实际应该调用真实API
                fallback_topics = self._get_fallback_topics()
                for i, topic in enumerate(fallback_topics[:limit]):
                    items.append(HotListItem(
                        title=topic["title"],
                        platform=PlatformType.XIAOHONGSHU,
                        url=topic.get("url", ""),
                        hot_score=topic.get("score", 80) - i * 2,
                        rank=i + 1,
                        tags=["小红书", "热门"],
                        extra={"source": "xiaohongshu_trending", "is_fallback": True}
                    ))
                
                return items, ""
                
        except Exception as e:
            error_msg = f"小红书热榜获取失败: {str(e)}"
            logger.error(f"[XiaohongshuHot] {error_msg}")
            return [], error_msg
    
    def _get_fallback_topics(self) -> List[Dict]:
        """备用热门话题（当API失败时）"""
        return [
            {"title": "逆袭成功！普通人的赚钱秘籍", "score": 95},
            {"title": "月入过万不是梦，这个方法太绝了", "score": 92},
            {"title": "35岁被裁后，我靠这个月入3万", "score": 90},
            {"title": "宝妈副业推荐：在家也能赚钱", "score": 88},
            {"title": "从零开始的创业故事", "score": 85},
            {"title": "靠这个技能，我实现了财务自由", "score": 83},
            {"title": "每天2小时，月入5位数的秘密", "score": 80},
            {"title": "打工人必看：副业赚钱指南", "score": 78},
        ]


class KuaishouHotSource:
    """快手热榜源"""
    
    async def fetch(self, limit: int = 20) -> Tuple[List[HotListItem], str]:
        """获取快手热榜"""
        items = []
        
        try:
            # 快手热榜API
            url = "https://www.kuaishou.com/rest/n/search/hot?type=12"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                
                if r.status_code == 200:
                    data = r.json()
                    hot_list = data.get("data", {}).get("hotList", [])
                    
                    for i, item in enumerate(hot_list[:limit]):
                        title = item.get("name", "")
                        if title:
                            items.append(HotListItem(
                                title=title,
                                platform=PlatformType.KUAISHOU,
                                hot_score=item.get("hot", 80) / 10,
                                rank=i + 1,
                                tags=["快手", "热榜"],
                                extra={"source": "kuaishou_hot"}
                            ))
                    
                    return items, ""
                else:
                    return [], f"HTTP {r.status_code}"
                    
        except Exception as e:
            error_msg = f"快手热榜获取失败: {str(e)}"
            logger.error(f"[KuaishouHot] {error_msg}")
            return [], error_msg


class BilibiliHotSource:
    """B站热榜源"""
    
    async def fetch(self, limit: int = 20) -> Tuple[List[HotListItem], str]:
        """获取B站热门"""
        items = []
        
        try:
            # B站热门视频API
            url = "https://api.bilibili.com/x/web-interface/ranking/v2"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Referer": "https://www.bilibili.com",
                })
                
                if r.status_code == 200:
                    data = r.json()
                    video_list = data.get("data", {}).get("list", [])
                    
                    for i, video in enumerate(video_list[:limit]):
                        title = video.get("title", "")
                        if title:
                            items.append(HotListItem(
                                title=title,
                                platform=PlatformType.BILIBILI,
                                url=f"https://www.bilibili.com/video/{video.get('bvid', '')}",
                                play_count=video.get("stat", {}).get("view", 0),
                                like_count=video.get("stat", {}).get("like", 0),
                                author=video.get("owner", {}).get("name", ""),
                                hot_score=video.get("score", 80) / 10 if video.get("score") else 80 - i * 2,
                                rank=i + 1,
                                tags=["B站", "热门"],
                                extra={"source": "bilibili_hot", "original_data": video}
                            ))
                    
                    return items, ""
                else:
                    return [], f"HTTP {r.status_code}"
                    
        except Exception as e:
            error_msg = f"B站热榜获取失败: {str(e)}"
            logger.error(f"[BilibiliHot] {error_msg}")
            return [], error_msg


class MultiSourceHotlistAggregator:
    """
    多源热榜聚合器
    
    【现状说明】
    - 抖音(TikHub): 真实实时数据（需要配置TIKHUB_API_KEY）
    - 小红书: 当前使用预设fallback（需要接入Playwright或第三方服务）
    - 快手/B站: 尝试调用公开API（稳定性不确定）
    
    建议：对于IP内容创作，优先使用竞品监控（competitor_monitor_service）
    热榜数据更适合泛娱乐类账号
    """
    
    def __init__(self):
        self.sources = {
            PlatformType.DOUYIN: DouyinHotSource(),      # 真实数据源
            # PlatformType.XIAOHONGSHU: XiaohongshuHotSource(),  # 预设数据，暂时禁用
            # PlatformType.KUAISHOU: KuaishouHotSource(),        # API不稳定
            # PlatformType.BILIBILI: BilibiliHotSource(),        # API可用性待验证
        }
        
        # 各平台权重（用于最终排序）
        self.platform_weights = {
            PlatformType.DOUYIN: 1.0,      # 抖音权重最高
            PlatformType.XIAOHONGSHU: 0.9,
            PlatformType.KUAISHOU: 0.8,
            PlatformType.BILIBILI: 0.7,
        }
    
    async def fetch_all(
        self,
        limit_per_platform: int = 15,
        platforms: Optional[List[PlatformType]] = None
    ) -> MultiSourceResult:
        """
        获取所有平台的热榜
        
        Args:
            limit_per_platform: 每个平台获取的数量
            platforms: 指定平台列表，None表示全部
        
        Returns:
            MultiSourceResult
        """
        platforms = platforms or list(self.sources.keys())
        
        # 并行获取所有平台
        tasks = []
        for platform in platforms:
            source = self.sources.get(platform)
            if source:
                tasks.append(self._fetch_with_timeout(source, platform, limit_per_platform))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        all_items = []
        source_stats = {}
        errors = []
        
        for platform, result in zip(platforms, results):
            if isinstance(result, Exception):
                errors.append(f"{platform.value}: {str(result)}")
                source_stats[platform.value] = 0
            else:
                items, error = result
                if items:
                    all_items.extend(items)
                    source_stats[platform.value] = len(items)
                if error:
                    errors.append(f"{platform.value}: {error}")
        
        return MultiSourceResult(
            items=all_items,
            source_stats=source_stats,
            fetch_time=datetime.utcnow(),
            errors=errors
        )
    
    async def _fetch_with_timeout(
        self,
        source,
        platform: PlatformType,
        limit: int,
        timeout: float = 20.0
    ) -> Tuple[List[HotListItem], str]:
        """带超时的获取"""
        try:
            return await asyncio.wait_for(
                source.fetch(limit),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return [], f"{platform.value}获取超时"
        except Exception as e:
            return [], f"{platform.value}异常: {str(e)}"
    
    async def fetch_best(
        self,
        ip_profile: Dict[str, Any],
        total_limit: int = 20,
        min_sources: int = 1
    ) -> MultiSourceResult:
        """
        获取最适合IP的热榜
        
        策略：
        1. 获取多源数据
        2. 按IP画像过滤和排序
        3. 确保多样性（各平台都有）
        
        Args:
            ip_profile: IP画像
            total_limit: 最终返回数量
            min_sources: 最少需要几个源成功
        """
        # 1. 获取所有热榜
        result = await self.fetch_all(limit_per_platform=total_limit)
        
        # 2. 检查是否满足最小源要求
        successful_sources = sum(1 for count in result.source_stats.values() if count > 0)
        if successful_sources < min_sources:
            logger.warning(f"[MultiSource] Only {successful_sources} sources succeeded, minimum {min_sources} required")
        
        # 3. 按IP画像过滤和排序
        from app.services.smart_ip_matcher import SmartIPMatcher
        matcher = SmartIPMatcher()
        
        scored_items = []
        for item in result.items:
            match_score = matcher.calculate_match_score(item.title, ip_profile)
            # 综合得分 = 热度分 * 平台权重 + IP匹配分
            final_score = (
                item.hot_score * 0.3 * self.platform_weights.get(item.platform, 0.5) +
                match_score * 100 * 0.7
            )
            scored_items.append((item, final_score, match_score))
        
        # 4. 按分数排序
        scored_items.sort(key=lambda x: x[1], reverse=True)
        
        # 5. 确保平台多样性（不要全是一个平台的）
        diversified = self._ensure_diversity(
            [item for item, _, _ in scored_items],
            total_limit
        )
        
        # 6. 更新结果
        result.items = diversified
        return result
    
    def _ensure_diversity(
        self,
        items: List[HotListItem],
        total_limit: int,
        max_per_platform: int = 5
    ) -> List[HotListItem]:
        """确保平台多样性"""
        result = []
        platform_counts = {p: 0 for p in PlatformType}
        
        for item in items:
            if platform_counts[item.platform] < max_per_platform:
                result.append(item)
                platform_counts[item.platform] += 1
                
                if len(result) >= total_limit:
                    break
        
        return result
    
    def to_topic_data_list(self, result: MultiSourceResult) -> List[TopicData]:
        """转换为TopicData列表"""
        topics = []
        for item in result.items:
            # 将hot_score转换为0-5的score
            score = min(5.0, item.hot_score / 20) if item.hot_score > 0 else 3.0
            
            topic = TopicData(
                id=f"{item.platform.value}_{item.rank}_{hash(item.title) % 10000:04d}",
                title=item.title,
                original_title=item.title,
                platform=item.platform.value,
                url=item.url or "",
                tags=item.tags,
                score=score,
                source=f"{item.platform.value}_hot",
                extra={
                    "play_count": item.play_count,
                    "like_count": item.like_count,
                    "author": item.author,
                    "hot_score": item.hot_score,
                    "rank": item.rank,
                    **item.extra
                }
            )
            topics.append(topic)
        return topics


# ============== 便捷函数 ==============

_aggregator: Optional[MultiSourceHotlistAggregator] = None


def get_multi_source_aggregator() -> MultiSourceHotlistAggregator:
    """获取全局聚合器实例"""
    global _aggregator
    if _aggregator is None:
        _aggregator = MultiSourceHotlistAggregator()
    return _aggregator


async def fetch_multi_source_hotlist(
    ip_profile: Dict[str, Any],
    limit: int = 20
) -> MultiSourceResult:
    """
    便捷函数：获取多源热榜
    
    Args:
        ip_profile: IP画像
        limit: 返回数量
    
    Returns:
        MultiSourceResult
    """
    aggregator = get_multi_source_aggregator()
    return await aggregator.fetch_best(ip_profile, limit)


async def fetch_hotlist_fallback(
    ip_profile: Dict[str, Any],
    limit: int = 12
) -> List[TopicData]:
    """
    兜底函数：当所有API失败时返回内置热榜
    
    这个函数用于确保即使所有外部API都失败，
    也能返回一些高质量的选题
    """
    from app.services.datasource.builtin_viral_repository import get_builtin_repository
    
    # 1. 先尝试多源聚合
    aggregator = get_multi_source_aggregator()
    result = await aggregator.fetch_best(ip_profile, limit)
    
    if result.items and len(result.items) >= limit // 2:
        # 成功获取到足够数据
        logger.info(f"[HotlistFallback] Got {len(result.items)} items from multi-source")
        return aggregator.to_topic_data_list(result)
    
    # 2. 多源不足，补充内置库
    logger.warning(f"[HotlistFallback] Multi-source returned {len(result.items)} items, using builtin fallback")
    
    builtin_repo = get_builtin_repository()
    builtin_topics = builtin_repo.get_topics_for_ip(ip_profile, limit)
    
    # 3. 合并结果（如果有部分多源数据）
    existing_topics = aggregator.to_topic_data_list(result) if result.items else []
    
    # 去重合并
    seen_titles = {t.title for t in existing_topics}
    for topic in builtin_topics:
        if topic.title not in seen_titles:
            existing_topics.append(topic)
            seen_titles.add(topic.title)
        
        if len(existing_topics) >= limit:
            break
    
    return existing_topics[:limit]
