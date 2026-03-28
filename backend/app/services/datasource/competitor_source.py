"""
竞品爆款数据源 - 核心数据源(P0)

核心思路：
1. 从配置的竞品账号抓取近期爆款视频
2. 基于IP标签筛选最相关的竞品内容
3. 提取爆款的内容结构，而非简单复制标题

为什么有效：
- 同类IP已经验证过的选题角度
- 受众画像高度重合
- 爆款的内核（冲突、情绪）可复用
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import httpx

from .base import DataSource, DataSourceConfig, TopicData, DataSourcePriority

logger = logging.getLogger(__name__)


@dataclass
class CompetitorVideo:
    """竞品视频数据结构"""
    video_id: str
    title: str
    desc: str
    author: str
    author_id: str
    platform: str
    
    # 数据表现
    play_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    
    # 内容分析
    tags: List[str] = None
    content_type: str = ""  # money/emotion/skill/life
    
    # 时间
    create_time: datetime = None
    fetched_at: datetime = None
    
    # 内容结构分析（用于重构）
    content_structure: Dict[str, Any] = None


class CompetitorTopicDataSource(DataSource):
    """
    竞品爆款数据源 - P0级核心数据源
    
    数据来源：
    1. 数据库中已抓取的竞品视频
    2. 实时从竞品账号抓取（需要配置API）
    
    匹配逻辑：
    - 基于IP的标签体系（宝妈/创业/赚钱/情感）
    - 筛选同类竞品的高播放量视频
    - 按内容类型分布（4-3-2-1矩阵）
    """
    
    def __init__(self, db_session=None):
        config = DataSourceConfig(
            source_id="competitor_topics",
            name="竞品爆款选题",
            priority=DataSourcePriority.P0,  # 最高优先级
            enabled=True,
            timeout=15,
            max_results=30,
            cache_ttl=3600,  # 1小时缓存
        )
        super().__init__(config)
        self.db = db_session
        
        # API配置（可选，用于实时抓取）
        import os
        self.tikhub_key = os.environ.get("TIKHUB_API_KEY", "")
        self.shunwei_key = os.environ.get("SHUNWEI_API_KEY", "")
    
    def is_available(self) -> bool:
        """检查是否有竞品数据可用"""
        # 如果有数据库连接，检查是否有竞品数据
        if self.db:
            return True
        # 否则检查是否有API配置
        return bool(self.tikhub_key or self.shunwei_key)
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """
        获取竞品爆款选题
        
        策略：
        1. 从数据库获取该IP配置的竞品账号的近期爆款
        2. 基于IP标签筛选最相关的内容
        3. 按内容类型分布返回
        """
        topics = []
        
        # 1. 获取竞品账号列表
        competitor_accounts = await self._get_competitor_accounts(ip_profile)
        if not competitor_accounts:
            logger.warning("[CompetitorSource] No competitor accounts configured")
            return []
        
        # 2. 从数据库获取这些竞品的近期爆款
        videos = await self._fetch_from_database(competitor_accounts, ip_profile, limit)
        
        # 3. 如果数据库数据不足，尝试实时抓取
        if len(videos) < limit // 2:
            fetched = await self._fetch_from_api(competitor_accounts, ip_profile, limit - len(videos))
            videos.extend(fetched)
        
        # 4. 转换为TopicData
        for video in videos:
            topic = self._convert_to_topic(video, ip_profile)
            if topic:
                topics.append(topic)
        
        logger.info(f"[CompetitorSource] Fetched {len(topics)} topics from {len(competitor_accounts)} competitors")
        return topics[:limit]
    
    async def _get_competitor_accounts(self, ip_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取IP配置的竞品账号"""
        # 从IP配置中获取竞品账号
        competitors = ip_profile.get("competitors", [])
        
        if not competitors and self.db:
            # 从数据库查询
            try:
                from sqlalchemy import text
                result = self.db.execute(
                    text("SELECT * FROM competitor_accounts WHERE ip_id = :ip_id"),
                    {"ip_id": ip_profile.get("ip_id")}
                )
                competitors = [dict(row) for row in result.mappings()]
            except Exception as e:
                logger.warning(f"[CompetitorSource] DB query failed: {e}")
        
        return competitors
    
    async def _fetch_from_database(
        self, 
        competitors: List[Dict], 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[CompetitorVideo]:
        """从数据库获取竞品视频"""
        if not self.db:
            return []
        
        try:
            from sqlalchemy import text
            
            # 构建查询 - 获取近期高播放量视频
            competitor_ids = [c.get("competitor_id") for c in competitors]
            
            # 根据IP标签构建内容类型偏好
            ip_tags = self._extract_ip_tags(ip_profile)
            
            query = text("""
                SELECT * FROM competitor_videos 
                WHERE competitor_id = ANY(:competitor_ids)
                AND fetched_at > NOW() - INTERVAL '7 days'
                AND play_count > 10000  -- 只取爆款
                ORDER BY play_count DESC
                LIMIT :limit
            """)
            
            result = self.db.execute(
                query,
                {"competitor_ids": competitor_ids, "limit": limit * 2}
            )
            
            videos = []
            for row in result.mappings():
                video = CompetitorVideo(
                    video_id=str(row.get("video_id", "")),
                    title=row.get("title", ""),
                    desc=row.get("desc", ""),
                    author=row.get("author", ""),
                    author_id=row.get("author_id", ""),
                    platform=row.get("platform", ""),
                    play_count=row.get("play_count", 0),
                    like_count=row.get("like_count", 0),
                    comment_count=row.get("comment_count", 0),
                    tags=row.get("tags", []),
                    content_type=row.get("content_type", ""),
                    create_time=row.get("create_time"),
                    fetched_at=row.get("fetched_at"),
                    content_structure=row.get("content_structure", {}),
                )
                videos.append(video)
            
            return videos
            
        except Exception as e:
            logger.error(f"[CompetitorSource] DB fetch failed: {e}")
            return []
    
    async def _fetch_from_api(
        self, 
        competitors: List[Dict], 
        ip_profile: Dict[str, Any], 
        limit: int
    ) -> List[CompetitorVideo]:
        """实时从API抓取竞品视频"""
        if not self.tikhub_key:
            return []
        
        videos = []
        
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            for competitor in competitors[:3]:  # 最多取前3个竞品
                try:
                    platform = competitor.get("platform", "douyin")
                    author_id = competitor.get("external_id", "")
                    
                    if platform == "douyin" and author_id:
                        fetched = await self._fetch_douyin_videos(client, author_id, limit // 3)
                        videos.extend(fetched)
                        
                except Exception as e:
                    logger.warning(f"[CompetitorSource] API fetch failed for {competitor.get('name')}: {e}")
                    continue
        
        return videos
    
    async def _fetch_douyin_videos(
        self, 
        client: httpx.AsyncClient, 
        sec_uid: str, 
        limit: int
    ) -> List[CompetitorVideo]:
        """抓取抖音用户视频"""
        try:
            resp = await client.get(
                "https://api.tikhub.io/api/v1/douyin/app/v3/fetch_user_post_videos",
                headers={"Authorization": f"Bearer {self.tikhub_key}"},
                params={"sec_user_id": sec_uid, "count": limit * 2},
                timeout=30
            )
            
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            if data.get("code") != 200:
                return []
            
            videos_data = data.get("data", {}).get("aweme_list", [])
            videos = []
            
            for v in videos_data[:limit]:
                stats = v.get("statistics", {})
                video = CompetitorVideo(
                    video_id=str(v.get("aweme_id", "")),
                    title=v.get("desc", "")[:100],
                    desc=v.get("desc", ""),
                    author=v.get("author", {}).get("nickname", ""),
                    author_id=sec_uid,
                    platform="douyin",
                    play_count=stats.get("play_count", 0),
                    like_count=stats.get("digg_count", 0),
                    comment_count=stats.get("comment_count", 0),
                    share_count=stats.get("share_count", 0),
                    tags=self._extract_tags_from_desc(v.get("desc", "")),
                )
                videos.append(video)
            
            return videos
            
        except Exception as e:
            logger.warning(f"[CompetitorSource] Douyin fetch failed: {e}")
            return []
    
    def _extract_tags_from_desc(self, desc: str) -> List[str]:
        """从描述中提取标签"""
        import re
        tags = re.findall(r'#([^#\s]+)', desc)
        return tags[:10]
    
    def _extract_ip_tags(self, ip_profile: Dict[str, Any]) -> List[str]:
        """提取IP的核心标签"""
        tags = []
        
        # 从IP配置中提取标签
        expertise = ip_profile.get("expertise", "")
        target_audience = ip_profile.get("target_audience", "")
        content_direction = ip_profile.get("content_direction", "")
        
        # 分词提取关键标签
        for text in [expertise, target_audience, content_direction]:
            if text:
                # 简单的分词，实际可以用jieba
                words = text.replace("、", ",").replace("/", ",").split(",")
                tags.extend([w.strip() for w in words if len(w.strip()) > 1])
        
        return list(set(tags))[:10]
    
    def _convert_to_topic(self, video: CompetitorVideo, ip_profile: Dict[str, Any]) -> Optional[TopicData]:
        """将竞品视频转换为选题"""
        if not video.title:
            return None
        
        # 构建选题ID
        topic_id = f"comp_{video.platform}_{video.video_id[:16]}"
        
        # 计算分数（基于竞品数据表现）
        base_score = 4.0
        
        # 播放量加成（爆款权重）
        if video.play_count > 100000:
            base_score += 0.5
        elif video.play_count > 50000:
            base_score += 0.3
        elif video.play_count > 10000:
            base_score += 0.1
        
        # 互动率加成
        if video.play_count > 0:
            engagement_rate = (video.like_count + video.comment_count + video.share_count) / video.play_count
            if engagement_rate > 0.1:  # 互动率超过10%
                base_score += 0.3
            elif engagement_rate > 0.05:
                base_score += 0.2
        
        # 时效性减分（越新越好）
        if video.create_time:
            days_old = (datetime.now() - video.create_time).days
            if days_old > 30:
                base_score -= 0.3
            elif days_old > 14:
                base_score -= 0.1
        
        # 构建标签
        tags = video.tags or []
        tags.extend(["竞品爆款", video.platform, video.content_type or "未分类"])
        tags = list(set(tags))[:5]
        
        # 构建content_structure用于后续重构
        content_structure = video.content_structure or {}
        if not content_structure:
            content_structure = self._analyze_content_structure(video)
        
        return TopicData(
            id=topic_id,
            title=video.title,
            original_title=video.title,
            platform=video.platform,
            url=f"https://www.douyin.com/video/{video.video_id}" if video.platform == "douyin" else "",
            tags=tags,
            score=min(5.0, base_score),
            source=self.config.source_id,
            extra={
                "competitor_author": video.author,
                "competitor_author_id": video.author_id,
                "play_count": video.play_count,
                "like_count": video.like_count,
                "comment_count": video.comment_count,
                "content_type": video.content_type,
                "content_structure": content_structure,  # 用于内容重构
                "is_competitor_topic": True,
                "needs_rewrite": True,  # 标记需要重构而非简单改写
            }
        )
    
    def _analyze_content_structure(self, video: CompetitorVideo) -> Dict[str, Any]:
        """
        分析内容结构，提取可用于重构的元素
        
        返回结构：
        - hook: 开头钩子类型
        - conflict: 冲突点
        - emotion: 情绪类型
        - solution: 解决方案暗示
        """
        title = video.title
        desc = video.desc
        
        structure = {
            "hook_type": self._detect_hook_type(title),
            "conflict_point": self._extract_conflict(title, desc),
            "emotion_type": self._detect_emotion(title),
            "solution_hint": self._detect_solution(title, desc),
            "target_audience": self._detect_audience(title),
        }
        
        return structure
    
    def _detect_hook_type(self, text: str) -> str:
        """检测开头钩子类型"""
        hooks = {
            "数字": [r'\d+', r'第[一二三四五六七八九十\d]+'],
            "疑问": [r'为什么', r'怎么', r'如何', r'什么', r'吗[？?]'],
            "冲突": [r'但是', r'然而', r'却', r'没想到'],
            "对比": [r'vs', r'对比', r'区别', r'差距'],
            "结果前置": [r'终于', r'最后', r'结局', r'结果'],
        }
        
        for hook_type, patterns in hooks.items():
            for pattern in patterns:
                import re
                if re.search(pattern, text):
                    return hook_type
        
        return "陈述"
    
    def _extract_conflict(self, title: str, desc: str) -> str:
        """提取冲突点"""
        # 常见的冲突词
        conflict_words = ['负债', '失业', '离婚', '被骗', '失败', '困境', '迷茫', '焦虑', '压力']
        
        for word in conflict_words:
            if word in title or word in desc:
                return word
        
        return ""
    
    def _detect_emotion(self, text: str) -> str:
        """检测情绪类型"""
        emotions = {
            "共鸣": ['感动', '心疼', '理解', '同款'],
            "励志": ['逆袭', '成功', '坚持', '努力', '奋斗'],
            "愤怒": ['不公平', '被骗', '坑', '气'],
            "好奇": ['秘密', '真相', '原来', '没想到'],
            "焦虑": ['怎么办', '迷茫', '焦虑', '压力'],
        }
        
        for emotion, words in emotions.items():
            for word in words:
                if word in text:
                    return emotion
        
        return "中性"
    
    def _detect_solution(self, title: str, desc: str) -> str:
        """检测解决方案暗示"""
        solution_words = ['方法', '技巧', '攻略', '秘诀', '经验', '步骤', '教程']
        
        for word in solution_words:
            if word in title or word in desc:
                return word
        
        return ""
    
    def _detect_audience(self, text: str) -> str:
        """检测目标受众"""
        audiences = {
            "宝妈": ['宝妈', '妈妈', '带娃', '全职妈妈'],
            "职场": ['上班族', '打工人', '职场', '辞职'],
            "创业": ['创业', '副业', '赚钱', '变现'],
            "学生": ['学生', '大学生', '考研', '毕业'],
        }
        
        for audience, words in audiences.items():
            for word in words:
                if word in text:
                    return audience
        
        return ""
