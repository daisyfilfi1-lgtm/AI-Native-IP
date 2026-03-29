"""
竞品账号监控服务

这才是真正有效的爆款获取方式：
1. 不抓平台热榜（泛娱乐、不匹配IP）
2. 监控同类IP的竞品账号
3. 抓取他们的近期爆款视频
4. 数据天然与IP同领域
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import quote
import os

import httpx

from app.services.tikhub_client import (
    is_configured as tikhub_configured,
    fetch_douyin_web_one_video_by_share_url,
)
from app.services.datasource.base import TopicData

logger = logging.getLogger(__name__)


@dataclass
class CompetitorVideo:
    """竞品视频数据"""
    video_id: str
    title: str
    author: str
    author_sec_uid: str
    play_count: int
    like_count: int
    comment_count: int
    share_count: int
    publish_time: Optional[datetime]
    url: str
    cover_url: str = ""
    tags: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoredCompetitor:
    """被监控的竞品账号"""
    sec_uid: str
    nickname: str
    platform: str = "douyin"
    follower_count: int = 0
    notes: str = ""  # 为什么监控这个账号
    last_fetch_time: Optional[datetime] = None
    avg_play_count: int = 0


class CompetitorMonitorService:
    """
    竞品账号监控服务
    
    核心思路：监控同类IP的竞品账号，抓取他们的爆款
    比平台热榜更精准，因为竞品天然与IP同领域
    """
    
    # 预设的竞品账号库（按IP类型分类）
    PRESET_COMPETITORS = {
        "mom_entrepreneur": [  # 宝妈创业类
            {"sec_uid": "MS4wLjABAAAAF5rv57l7D2h0jJWd04cQ4yhFz4z0OeRz3Z7YxL3J7mG", "nickname": "示例宝妈账号1", "notes": "宝妈副业分享"},
            # 实际使用时从数据库或配置文件加载
        ],
        "side_hustle": [  # 副业赚钱类
            # ...
        ],
        "knowledge_paid": [  # 知识付费类
            # ...
        ],
    }
    
    def __init__(self):
        self.api_key = os.environ.get("TIKHUB_API_KEY", "").strip()
        self.base_url = os.environ.get("TIKHUB_BASE_URL", "https://api.tikhub.io")
    
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}
    
    async def fetch_user_videos_tikhub(
        self,
        sec_uid: str,
        count: int = 20
    ) -> Tuple[List[CompetitorVideo], str]:
        """
        使用TikHub API获取用户发布的视频
        """
        if not tikhub_configured():
            return [], "TikHub未配置"
        
        videos = []
        error_msg = ""
        
        try:
            logger.info(f"[CompetitorMonitor] Fetching videos for user: {sec_uid[:20]}...")
            
            timeout = httpx.Timeout(30.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                url = f"{self.base_url}/api/v1/douyin/app/v3/fetch_user_post_videos"
                r = await client.get(
                    url,
                    headers=self._headers(),
                    params={
                        "sec_user_id": sec_uid,
                        "max_cursor": 0,
                        "count": count
                    }
                )
                
                if r.status_code != 200:
                    return [], f"HTTP {r.status_code}"
                
                data = r.json()
                if data.get("code") != 200:
                    return [], f"API Error: {data.get('message')}"
                
                aweme_list = data.get("data", {}).get("aweme_list", [])
                
                for item in aweme_list:
                    try:
                        video = self._parse_video_item(item, sec_uid)
                        if video:
                            videos.append(video)
                    except Exception as e:
                        logger.warning(f"Failed to parse video item: {e}")
                        continue
                
                logger.info(f"[CompetitorMonitor] Fetched {len(videos)} videos from {sec_uid[:20]}")
                return videos, ""
                
        except Exception as e:
            error_msg = f"获取用户视频失败: {str(e)}"
            logger.error(f"[CompetitorMonitor] {error_msg}")
            return [], error_msg
    
    def _parse_video_item(self, item: Dict, sec_uid: str) -> Optional[CompetitorVideo]:
        """解析视频数据"""
        if not item or not isinstance(item, dict):
            return None
        
        aweme_id = item.get("aweme_id", "")
        desc = item.get("desc", "")
        
        if not desc:
            return None
        
        # 提取统计数据
        stats = item.get("statistics", {})
        play_count = stats.get("play_count", 0)
        like_count = stats.get("digg_count", 0)
        comment_count = stats.get("comment_count", 0)
        share_count = stats.get("share_count", 0)
        
        # 提取作者信息
        author = item.get("author", {})
        nickname = author.get("nickname", "")
        author_sec_uid = author.get("sec_uid", sec_uid)
        
        # 提取标签
        text_extra = item.get("text_extra", [])
        hashtags = [tag.get("hashtag_name", "") for tag in text_extra if tag.get("hashtag_name")]
        
        # 封面
        video_info = item.get("video", {})
        cover_url = video_info.get("cover", {}).get("url_list", [""])[0] if isinstance(video_info, dict) else ""
        
        # 发布时间
        create_time = item.get("create_time")
        publish_time = datetime.fromtimestamp(create_time) if create_time else None
        
        return CompetitorVideo(
            video_id=aweme_id,
            title=desc[:200],  # 限制长度
            author=nickname,
            author_sec_uid=author_sec_uid,
            play_count=play_count,
            like_count=like_count,
            comment_count=comment_count,
            share_count=share_count,
            publish_time=publish_time,
            url=f"https://www.douyin.com/video/{aweme_id}" if aweme_id else "",
            cover_url=cover_url,
            tags=hashtags[:5],
            raw_data=item
        )
    
    def filter_viral_videos(
        self,
        videos: List[CompetitorVideo],
        min_play_count: int = 10000,
        days_back: int = 30
    ) -> List[CompetitorVideo]:
        """
        筛选爆款视频
        
        Args:
            videos: 视频列表
            min_play_count: 最小播放量
            days_back: 最近多少天内
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        viral = []
        for video in videos:
            # 播放量达标
            if video.play_count < min_play_count:
                continue
            
            # 时间范围内
            if video.publish_time and video.publish_time < cutoff_date:
                continue
            
            viral.append(video)
        
        # 按播放量排序
        viral.sort(key=lambda x: x.play_count, reverse=True)
        return viral
    
    async def monitor_competitors(
        self,
        competitors: List[MonitoredCompetitor],
        videos_per_user: int = 10,
        min_play_count: int = 10000
    ) -> Tuple[List[CompetitorVideo], Dict[str, Any]]:
        """
        监控多个竞品账号，获取他们的爆款
        
        Args:
            competitors: 竞品账号列表
            videos_per_user: 每个账号取多少视频
            min_play_count: 最小播放量阈值
        
        Returns:
            (爆款视频列表, 统计信息)
        """
        all_viral_videos = []
        stats = {
            "total_competitors": len(competitors),
            "successful_fetches": 0,
            "failed_fetches": 0,
            "total_videos": 0,
            "viral_videos": 0,
            "by_competitor": {}
        }
        
        # 并行获取所有竞品
        tasks = []
        for comp in competitors:
            tasks.append(self._fetch_and_filter(
                comp, videos_per_user, min_play_count
            ))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for competitor, result in zip(competitors, results):
            comp_key = competitor.nickname or competitor.sec_uid[:10]
            
            if isinstance(result, Exception):
                stats["failed_fetches"] += 1
                stats["by_competitor"][comp_key] = {
                    "status": "error",
                    "error": str(result)
                }
            else:
                videos, is_success = result
                if is_success:
                    stats["successful_fetches"] += 1
                    stats["total_videos"] += len(videos) * 2  # 估算原始数量
                    stats["viral_videos"] += len(videos)
                    all_viral_videos.extend(videos)
                    stats["by_competitor"][comp_key] = {
                        "status": "success",
                        "viral_count": len(videos)
                    }
                else:
                    stats["failed_fetches"] += 1
                    stats["by_competitor"][comp_key] = {
                        "status": "error",
                        "error": "Fetch failed"
                    }
        
        # 去重（按标题相似度）
        unique_videos = self._deduplicate_videos(all_viral_videos)
        
        # 最终排序
        unique_videos.sort(key=lambda x: x.play_count, reverse=True)
        
        return unique_videos, stats
    
    async def _fetch_and_filter(
        self,
        competitor: MonitoredCompetitor,
        videos_per_user: int,
        min_play_count: int
    ) -> Tuple[List[CompetitorVideo], bool]:
        """获取并筛选单个竞品的视频"""
        videos, error = await self.fetch_user_videos_tikhub(
            competitor.sec_uid,
            count=videos_per_user * 2  # 多取一些用于筛选
        )
        
        if error:
            return [], False
        
        viral = self.filter_viral_videos(videos, min_play_count)
        return viral, True
    
    def _deduplicate_videos(
        self,
        videos: List[CompetitorVideo],
        similarity_threshold: float = 0.8
    ) -> List[CompetitorVideo]:
        """按标题相似度去重"""
        unique = []
        
        for video in videos:
            is_duplicate = False
            for existing in unique:
                if self._title_similarity(video.title, existing.title) > similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(video)
        
        return unique
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """计算标题相似度（简化版）"""
        # 使用简单的字符重叠度
        set1 = set(title1.lower())
        set2 = set(title2.lower())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def videos_to_topics(self, videos: List[CompetitorVideo]) -> List[TopicData]:
        """转换为TopicData列表"""
        topics = []
        
        for i, video in enumerate(videos):
            # 计算分数 (0-5)
            score = min(5.0, video.play_count / 50000) if video.play_count > 0 else 3.0
            
            topic = TopicData(
                id=f"competitor_{video.author}_{video.video_id}_{i}",
                title=video.title,
                original_title=video.title,
                platform="douyin",
                url=video.url,
                tags=video.tags + ["竞品爆款", video.author],
                score=score,
                source="competitor_monitor",
                likes=video.like_count,
                comments=video.comment_count,
                shares=video.share_count,
                extra={
                    "competitor_author": video.author,
                    "competitor_sec_uid": video.author_sec_uid,
                    "play_count": video.play_count,
                    "publish_time": video.publish_time.isoformat() if video.publish_time else None,
                    "is_competitor_topic": True,
                    "needs_rewrite": True,
                    "cover_url": video.cover_url,
                }
            )
            topics.append(topic)
        
        return topics


# ============== 与IP绑定的竞品管理 ==============

class IPCompetitorManager:
    """
    IP竞品管理器
    
    每个IP有自己的竞品账号列表
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.monitor_service = CompetitorMonitorService()
    
    async def get_competitors_for_ip(self, ip_id: str) -> List[MonitoredCompetitor]:
        """获取IP绑定的竞品账号"""
        # TODO: 从数据库查询
        # 临时返回预设的竞品
        return [
            MonitoredCompetitor(
                sec_uid="MS4wLjABAAAAF5rv57l7D2h0jJWd04cQ4yhFz4z0OeRz3Z7YxL3J7mG",
                nickname="示例竞品账号",
                platform="douyin",
                notes="宝妈创业类竞品"
            )
        ]
    
    async def fetch_viral_topics_for_ip(
        self,
        ip_id: str,
        ip_profile: Dict[str, Any],
        limit: int = 12
    ) -> Tuple[List[TopicData], Dict[str, Any]]:
        """
        为IP获取竞品爆款选题
        
        这是真正有效的选题获取方式：
        1. 获取IP绑定的竞品账号
        2. 抓取竞品的近期爆款
        3. 返回已验证的爆款选题
        """
        # 1. 获取竞品账号
        competitors = await self.get_competitors_for_ip(ip_id)
        
        if not competitors:
            logger.warning(f"[IPCompetitorManager] No competitors configured for IP: {ip_id}")
            return [], {"error": "No competitors configured"}
        
        # 2. 监控竞品获取爆款
        viral_videos, stats = await self.monitor_service.monitor_competitors(
            competitors=competitors,
            videos_per_user=15,
            min_play_count=10000  # 至少1万播放才算爆款
        )
        
        # 3. 转换为TopicData
        topics = self.monitor_service.videos_to_topics(viral_videos[:limit])
        
        logger.info(f"[IPCompetitorManager] Fetched {len(topics)} viral topics for IP: {ip_id}")
        
        return topics, stats


# ============== 便捷函数 ==============

_monitor_service: Optional[CompetitorMonitorService] = None
_ip_manager: Optional[IPCompetitorManager] = None


def get_competitor_monitor_service() -> CompetitorMonitorService:
    """获取全局监控服务"""
    global _monitor_service
    if _monitor_service is None:
        _monitor_service = CompetitorMonitorService()
    return _monitor_service


def get_ip_competitor_manager(db_session=None) -> IPCompetitorManager:
    """获取IP竞品管理器"""
    global _ip_manager
    if _ip_manager is None:
        _ip_manager = IPCompetitorManager(db_session)
    return _ip_manager


async def fetch_viral_from_competitors(
    ip_id: str,
    ip_profile: Dict[str, Any],
    limit: int = 12,
    db_session=None
) -> List[TopicData]:
    """
    便捷函数：从竞品获取爆款选题
    """
    manager = get_ip_competitor_manager(db_session)
    topics, stats = await manager.fetch_viral_topics_for_ip(ip_id, ip_profile, limit)
    
    if not topics:
        logger.warning(f"[fetch_viral_from_competitors] No topics from competitors, using fallback")
        # 降级到内置库
        from app.services.datasource.builtin_viral_repository import get_builtin_repository
        repo = get_builtin_repository()
        return repo.get_topics_for_ip(ip_profile, limit)
    
    return topics
