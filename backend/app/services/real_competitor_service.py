"""
真实竞品数据源服务

直接使用数据库中的竞品数据：
1. competitor_accounts - 竞品账号配置（已同步到Railway）
2. competitor_videos - 竞品视频数据（已抓取存储）

这比热榜更精准，因为：
- 竞品是同类IP，数据天然匹配
- 视频已被竞品验证（有播放量数据）
- 不需要实时抓API，直接读数据库
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy import text

from app.services.datasource.base import TopicData
from app.services.datasource.competitor_source import CompetitorTopicDataSource
from app.services.smart_ip_matcher import get_smart_matcher

logger = logging.getLogger(__name__)


@dataclass
class CompetitorFetchResult:
    """竞品获取结果"""
    topics: List[TopicData]
    stats: Dict[str, Any]
    from_db: int
    from_api: int


class RealCompetitorService:
    """
    真实竞品服务
    
    从数据库读取竞品视频数据，无需担心API稳定性
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.data_source = CompetitorTopicDataSource(db_session=db_session)
    
    async def fetch_viral_topics(
        self,
        ip_id: str,
        ip_profile: Dict[str, Any],
        limit: int = 12,
        min_play_count: int = 10000,
        days_back: int = 30
    ) -> CompetitorFetchResult:
        """
        获取竞品爆款选题
        
        这是真正可靠的数据源：
        - 数据来自数据库（已抓取的竞品视频）
        - 同类IP的爆款（与目标IP同领域）
        - 有真实播放量验证
        """
        stats = {
            "competitor_count": 0,
            "total_videos": 0,
            "viral_videos": 0,
            "fetch_time": None,
        }
        
        if not self.db:
            logger.error("[RealCompetitor] No database session available")
            return CompetitorFetchResult(
                topics=[], stats=stats, from_db=0, from_api=0
            )
        
        start_time = datetime.utcnow()
        
        try:
            # 1. 获取该IP配置的竞品账号
            competitors = await self._get_competitor_accounts(ip_id)
            stats["competitor_count"] = len(competitors)
            
            if not competitors:
                logger.warning(f"[RealCompetitor] No competitors configured for IP: {ip_id}")
                return CompetitorFetchResult(
                    topics=[], stats=stats, from_db=0, from_api=0
                )
            
            # 2. 从数据库获取竞品视频
            videos = await self._fetch_videos_from_db(
                competitors=competitors,
                min_play_count=min_play_count,
                days_back=days_back,
                limit=limit * 2
            )
            
            stats["total_videos"] = len(videos)
            
            # 3. 转换为TopicData并排序
            topics = self._convert_to_topics(videos, ip_profile)
            
            # 4. 按IP匹配度进一步排序
            topics = self._rank_by_ip_match(topics, ip_profile)
            
            stats["viral_videos"] = len(topics)
            stats["fetch_time"] = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                f"[RealCompetitor] Fetched {len(topics)} viral topics from {len(competitors)} competitors"
            )
            
            return CompetitorFetchResult(
                topics=topics[:limit],
                stats=stats,
                from_db=len(topics),
                from_api=0
            )
            
        except Exception as e:
            logger.error(f"[RealCompetitor] Failed to fetch: {e}")
            return CompetitorFetchResult(
                topics=[], stats=stats, from_db=0, from_api=0
            )
    
    async def _get_competitor_accounts(self, ip_id: str) -> List[Dict[str, Any]]:
        """从数据库获取竞品账号列表"""
        try:
            result = self.db.execute(
                text("""
                    SELECT competitor_id, name, platform, notes, followers_display
                    FROM competitor_accounts
                    WHERE ip_id = :ip_id
                    ORDER BY created_at DESC
                """),
                {"ip_id": ip_id}
            )
            
            competitors = []
            for row in result.mappings():
                competitors.append({
                    "competitor_id": row.get("competitor_id"),
                    "name": row.get("name"),
                    "platform": row.get("platform", "douyin"),
                    "notes": row.get("notes", ""),
                    "followers": row.get("followers_display", ""),
                })
            
            return competitors
            
        except Exception as e:
            logger.error(f"[RealCompetitor] Failed to get competitors: {e}")
            return []
    
    async def _fetch_videos_from_db(
        self,
        competitors: List[Dict[str, Any]],
        min_play_count: int,
        days_back: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """从数据库获取竞品视频"""
        try:
            competitor_ids = [c["competitor_id"] for c in competitors]
            
            # 查询语句
            query = text("""
                SELECT 
                    v.video_id,
                    v.title,
                    v.desc,
                    v.author,
                    v.platform,
                    v.play_count,
                    v.like_count,
                    v.comment_count,
                    v.share_count,
                    v.create_time,
                    v.content_type,
                    v.tags,
                    c.name as competitor_name,
                    c.competitor_id
                FROM competitor_videos v
                JOIN competitor_accounts c ON v.competitor_id = c.competitor_id
                WHERE v.competitor_id = ANY(:competitor_ids)
                AND v.play_count >= :min_play_count
                AND v.fetched_at > NOW() - INTERVAL ':days_back days'
                ORDER BY v.play_count DESC
                LIMIT :limit
            """)
            
            result = self.db.execute(
                query,
                {
                    "competitor_ids": competitor_ids,
                    "min_play_count": min_play_count,
                    "days_back": days_back,
                    "limit": limit
                }
            )
            
            videos = []
            for row in result.mappings():
                videos.append(dict(row))
            
            logger.info(f"[RealCompetitor] Fetched {len(videos)} videos from DB")
            return videos
            
        except Exception as e:
            logger.error(f"[RealCompetitor] DB query failed: {e}")
            # 尝试备用查询（不使用时间过滤）
            return await self._fetch_videos_fallback(
                competitors, min_play_count, limit
            )
    
    async def _fetch_videos_fallback(
        self,
        competitors: List[Dict[str, Any]],
        min_play_count: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """备用查询（无时间过滤）"""
        try:
            competitor_ids = [c["competitor_id"] for c in competitors]
            
            query = text("""
                SELECT 
                    v.video_id,
                    v.title,
                    v.desc,
                    v.author,
                    v.platform,
                    v.play_count,
                    v.like_count,
                    v.comment_count,
                    v.share_count,
                    v.create_time,
                    v.content_type,
                    v.tags,
                    c.name as competitor_name,
                    c.competitor_id
                FROM competitor_videos v
                JOIN competitor_accounts c ON v.competitor_id = c.competitor_id
                WHERE v.competitor_id = ANY(:competitor_ids)
                AND v.play_count >= :min_play_count
                ORDER BY v.play_count DESC
                LIMIT :limit
            """)
            
            result = self.db.execute(
                query,
                {
                    "competitor_ids": competitor_ids,
                    "min_play_count": min_play_count,
                    "limit": limit
                }
            )
            
            videos = []
            for row in result.mappings():
                videos.append(dict(row))
            
            return videos
            
        except Exception as e:
            logger.error(f"[RealCompetitor] Fallback query also failed: {e}")
            return []
    
    def _convert_to_topics(
        self,
        videos: List[Dict[str, Any]],
        ip_profile: Dict[str, Any]
    ) -> List[TopicData]:
        """将视频数据转换为TopicData"""
        topics = []
        
        for video in videos:
            try:
                topic = self._video_to_topic(video, ip_profile)
                if topic:
                    topics.append(topic)
            except Exception as e:
                logger.warning(f"[RealCompetitor] Failed to convert video: {e}")
                continue
        
        return topics
    
    def _video_to_topic(
        self,
        video: Dict[str, Any],
        ip_profile: Dict[str, Any]
    ) -> Optional[TopicData]:
        """单个视频转换为TopicData"""
        title = video.get("title", "") or video.get("desc", "")
        if not title:
            return None
        
        video_id = str(video.get("video_id", ""))
        platform = video.get("platform", "douyin")
        play_count = video.get("play_count", 0)
        
        # 计算分数（基于播放量）
        score = min(5.0, max(3.0, play_count / 50000)) if play_count > 0 else 3.0
        
        # 构建URL
        url = ""
        if platform == "douyin":
            url = f"https://www.douyin.com/video/{video_id}"
        
        # 处理标签
        tags = video.get("tags", []) or []
        if isinstance(tags, str):
            tags = tags.split(",")
        tags = [t.strip() for t in tags if t.strip()]
        tags.extend(["竞品爆款", video.get("competitor_name", "")])
        tags = list(set(tags))[:5]
        
        return TopicData(
            id=f"comp_{platform}_{video_id[:16]}",
            title=title[:200],
            original_title=title[:200],
            platform=platform,
            url=url,
            tags=tags,
            score=score,
            source="competitor_db",
            likes=video.get("like_count", 0),
            comments=video.get("comment_count", 0),
            shares=video.get("share_count", 0),
            extra={
                "competitor_author": video.get("author", ""),
                "competitor_name": video.get("competitor_name", ""),
                "competitor_id": video.get("competitor_id", ""),
                "play_count": play_count,
                "content_type": video.get("content_type", ""),
                "is_competitor_topic": True,
                "needs_rewrite": True,
                "source": "database",  # 标记数据来源
            }
        )
    
    def _rank_by_ip_match(
        self,
        topics: List[TopicData],
        ip_profile: Dict[str, Any]
    ) -> List[TopicData]:
        """按IP匹配度排序"""
        matcher = get_smart_matcher()
        
        scored_topics = []
        for topic in topics:
            match_score = matcher.calculate_match_score(topic.title, ip_profile)
            # 综合得分 = 爆款分数 * 0.6 + 匹配分数 * 0.4
            combined_score = topic.score * 0.6 + match_score * 2.0  # match_score is 0-1
            scored_topics.append((topic, combined_score))
        
        # 按综合得分排序
        scored_topics.sort(key=lambda x: x[1], reverse=True)
        
        return [t[0] for t in scored_topics]
    
    async def get_competitor_stats(self, ip_id: str) -> Dict[str, Any]:
        """获取竞品统计数据"""
        if not self.db:
            return {}
        
        try:
            # 竞品账号数
            result = self.db.execute(
                text("SELECT COUNT(*) FROM competitor_accounts WHERE ip_id = :ip_id"),
                {"ip_id": ip_id}
            )
            account_count = result.scalar()
            
            # 视频总数
            result = self.db.execute(
                text("""
                    SELECT COUNT(*), AVG(play_count), MAX(play_count)
                    FROM competitor_videos v
                    JOIN competitor_accounts c ON v.competitor_id = c.competitor_id
                    WHERE c.ip_id = :ip_id
                """),
                {"ip_id": ip_id}
            )
            video_stats = result.fetchone()
            
            # 近期爆款数（7天内）
            result = self.db.execute(
                text("""
                    SELECT COUNT(*)
                    FROM competitor_videos v
                    JOIN competitor_accounts c ON v.competitor_id = c.competitor_id
                    WHERE c.ip_id = :ip_id
                    AND v.play_count > 10000
                    AND v.fetched_at > NOW() - INTERVAL '7 days'
                """),
                {"ip_id": ip_id}
            )
            recent_viral = result.scalar()
            
            return {
                "account_count": account_count,
                "total_videos": video_stats[0] if video_stats else 0,
                "avg_play_count": int(video_stats[1]) if video_stats and video_stats[1] else 0,
                "max_play_count": int(video_stats[2]) if video_stats and video_stats[2] else 0,
                "recent_viral_count": recent_viral,
            }
            
        except Exception as e:
            logger.error(f"[RealCompetitor] Failed to get stats: {e}")
            return {}


# ============== 便捷函数 ==============

_service: Optional[RealCompetitorService] = None


def get_real_competitor_service(db_session=None) -> RealCompetitorService:
    """获取全局服务实例"""
    global _service
    if _service is None:
        _service = RealCompetitorService(db_session)
    return _service


async def fetch_competitor_viral_topics(
    ip_id: str,
    ip_profile: Dict[str, Any],
    limit: int = 12,
    db_session=None
) -> List[TopicData]:
    """
    便捷函数：获取竞品爆款选题
    
    这是真正可靠的数据源：
    - 来自Railway数据库（已同步的竞品数据）
    - 竞品与IP同领域
    - 有真实播放量验证
    """
    service = get_real_competitor_service(db_session)
    result = await service.fetch_viral_topics(
        ip_id=ip_id,
        ip_profile=ip_profile,
        limit=limit
    )
    return result.topics
