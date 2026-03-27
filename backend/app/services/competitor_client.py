"""
竞品账号内容抓取客户端
通过抖音竞品账号（sec_uid）获取他们的热门视频
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# 竞品抖音账号列表（从竞品分析文档提取）
# 格式：sec_uid 或 share_url
DEFAULT_COMPETITORS = [
    # 可以从环境变量 TIKHUB_COMPETITOR_SEC_UIDS 配置
    # 示例格式：MS4wLjABAAAAF5rv57l7D2h0jJWd04cQ4yhFz4z0OeRz3Z7YxL3J7mG
]


class CompetitorClient:
    """竞品账号内容抓取客户端"""
    
    def __init__(self):
        self.api_key = os.environ.get("TIKHUB_API_KEY", "").strip()
        self.base_url = os.environ.get("TIKHUB_BASE_URL", "https://api.tikhub.io")
        # 从环境变量读取竞品账号列表
        competitors_str = os.environ.get("TIKHUB_COMPETITOR_SEC_UIDS", "")
        self.competitor_sec_uids = [
            uid.strip() 
            for uid in competitors_str.split(",") 
            if uid.strip()
        ]
    
    def is_configured(self) -> bool:
        return bool(self.api_key and self.competitor_sec_uids)
    
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}
    
    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送请求"""
        url = f"{self.base_url}{path}"
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.request(method, url, headers=self._headers(), **kwargs)
            try:
                body = r.json()
            except Exception:
                body = {"raw": r.text[:500]}
            if r.status_code >= 400:
                logger.warning(f"[Competitor] HTTP {r.status_code}: {body}")
                return {}
            return body
    
    async def fetch_user_videos(
        self, 
        sec_uid: str, 
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取抖音用户发布的视频
        GET /api/v1/douyin/app/v3/fetch_user_post_videos
        """
        try:
            logger.info(f"[Competitor] Fetching videos for user: {sec_uid[:20]}...")
            
            resp = await self._request(
                "GET",
                "/api/v1/douyin/app/v3/fetch_user_post_videos",
                params={
                    "sec_user_id": sec_uid,
                    "max_cursor": 0,
                    "count": count
                }
            )
            
            if resp.get("code") != 200:
                logger.warning(f"[Competitor] API error: {resp.get('message')}")
                return []
            
            data = resp.get("data", {})
            videos = data.get("aweme_list", []) if isinstance(data, dict) else []
            
            results = []
            for video in videos[:count]:
                if not isinstance(video, dict):
                    continue
                
                # 提取视频信息
                desc = video.get("desc", "")
                aweme_id = video.get("aweme_id", "")
                
                if not desc:
                    continue
                
                # 提取标签
                text_extra = video.get("text_extra", [])
                hashtags = [tag.get("hashtag_name", "") for tag in text_extra if tag.get("hashtag_name")]
                
                # 统计数据
                stats = video.get("statistics", {})
                
                results.append({
                    "id": f"comp_{aweme_id}",
                    "title": desc[:100],  # 抖音描述作为标题
                    "originalTitle": desc[:100],
                    "score": 4.5 + min(0.45, len(results) * 0.03),
                    "tags": ["抖音", "竞品"] + hashtags[:3],
                    "reason": "竞品账号热门视频",
                    "estimatedViews": str(stats.get("play_count", "—")),
                    "estimatedCompletion": 0,
                    "sourceUrl": f"https://www.douyin.com/video/{aweme_id}" if aweme_id else "",
                    "platform": "douyin_competitor",
                    "competitor_uid": sec_uid[:20],
                    "video_id": aweme_id,
                    "digg_count": stats.get("digg_count", 0),
                    "share_count": stats.get("share_count", 0),
                    "weight": 2.0,  # 竞品内容权重最高
                })
            
            logger.info(f"[Competitor] Fetched {len(results)} videos from user {sec_uid[:20]}...")
            return results
            
        except Exception as e:
            logger.error(f"[Competitor] Failed to fetch user videos: {e}")
            return []
    
    async def fetch_all_competitors(self, count_per_user: int = 5) -> List[Dict[str, Any]]:
        """
        从所有竞品账号获取视频
        """
        if not self.is_configured():
            logger.warning("[Competitor] Not configured")
            return []
        
        all_videos: List[Dict[str, Any]] = []
        
        for sec_uid in self.competitor_sec_uids:
            videos = await self.fetch_user_videos(sec_uid, count=count_per_user)
            all_videos.extend(videos)
        
        # 按点赞数排序
        sorted_videos = sorted(
            all_videos,
            key=lambda x: int(x.get("digg_count", 0)),
            reverse=True
        )
        
        # 去重
        seen = set()
        unique_videos = []
        for video in sorted_videos:
            key = video.get("title", "").lower().strip()[:50]
            if key and key not in seen:
                seen.add(key)
                unique_videos.append(video)
        
        logger.info(f"[Competitor] Total unique videos from all competitors: {len(unique_videos)}")
        return unique_videos


# 全局客户端
_competitor_client: Optional[CompetitorClient] = None


def get_competitor_client() -> CompetitorClient:
    """获取全局客户端"""
    global _competitor_client
    if _competitor_client is None:
        _competitor_client = CompetitorClient()
    return _competitor_client


async def get_competitor_videos(count_per_user: int = 5) -> List[Dict[str, Any]]:
    """便捷函数：获取竞品视频"""
    client = get_competitor_client()
    return await client.fetch_all_competitors(count_per_user=count_per_user)
