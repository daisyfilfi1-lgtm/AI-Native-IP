"""
小红书话题标签客户端
通过指定话题标签（如：宝妈创业、副业搞钱）定向获取笔记
比热榜更精准
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# 小敏IP相关的话题标签配置（可从环境变量读取）
DEFAULT_TOPIC_PAGE_IDS = [
    # 可以从环境变量 TIKHUB_XHS_TOPIC_PAGE_IDS 配置
    # 示例话题ID（需要替换为真实的）
]


class XHSTopicClient:
    """小红书话题标签客户端"""
    
    def __init__(self):
        self.api_key = os.environ.get("TIKHUB_API_KEY", "").strip()
        self.base_url = os.environ.get("TIKHUB_BASE_URL", "https://api.tikhub.io")
        # 从环境变量读取话题ID列表
        topic_ids_str = os.environ.get("TIKHUB_XHS_TOPIC_PAGE_IDS", "")
        self.topic_page_ids = [
            id.strip() 
            for id in topic_ids_str.split(",") 
            if id.strip()
        ]
    
    def is_configured(self) -> bool:
        return bool(self.api_key and self.topic_page_ids)
    
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
                logger.warning(f"[XHS Topic] HTTP {r.status_code}: {body}")
                return {}
            return body
    
    async def fetch_topic_info(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        获取话题信息
        GET /api/v1/xiaohongshu/app_v2/get_topic_info
        """
        try:
            resp = await self._request(
                "GET",
                "/api/v1/xiaohongshu/app_v2/get_topic_info",
                params={"page_id": page_id}
            )
            return resp.get("data") if isinstance(resp, dict) else None
        except Exception as e:
            logger.error(f"[XHS Topic] Failed to fetch topic info: {e}")
            return None
    
    async def fetch_topic_feed(
        self, 
        page_id: str, 
        sort: str = "hot",  # hot=热门, time=最新
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取话题下的笔记流
        GET /api/v1/xiaohongshu/app_v2/get_topic_feed
        """
        try:
            resp = await self._request(
                "GET",
                "/api/v1/xiaohongshu/app_v2/get_topic_feed",
                params={
                    "page_id": page_id,
                    "sort": sort,
                    "limit": limit
                }
            )
            
            data = resp.get("data") if isinstance(resp, dict) else None
            if not data:
                return []
            
            # 解析笔记列表
            notes = data if isinstance(data, list) else data.get("notes", [])
            
            results = []
            for note in notes[:limit]:
                if not isinstance(note, dict):
                    continue
                
                title = note.get("title") or note.get("desc", "")[:50]
                if not title:
                    continue
                
                results.append({
                    "id": f"xhs_topic_{page_id}_{len(results)}",
                    "title": title,
                    "originalTitle": title,
                    "score": 4.5 + min(0.45, len(results) * 0.03),
                    "tags": ["小红书", "话题", "竞品"],
                    "reason": f"小红书话题标签（精准匹配）",
                    "estimatedViews": "—",
                    "estimatedCompletion": 0,
                    "sourceUrl": note.get("note_url") or "",
                    "platform": "xiaohongshu_topic",
                    "topic_id": page_id,
                    "note_id": note.get("id"),
                })
            
            logger.info(f"[XHS Topic] Fetched {len(results)} notes from topic {page_id}")
            return results
            
        except Exception as e:
            logger.error(f"[XHS Topic] Failed to fetch topic feed: {e}")
            return []
    
    async def fetch_all_topics_feed(self, limit_per_topic: int = 5) -> List[Dict[str, Any]]:
        """
        从所有配置的话题标签中获取笔记
        """
        if not self.is_configured():
            logger.warning("[XHS Topic] Not configured")
            return []
        
        all_notes: List[Dict[str, Any]] = []
        
        for page_id in self.topic_page_ids:
            notes = await self.fetch_topic_feed(page_id, limit=limit_per_topic)
            all_notes.extend(notes)
        
        # 去重（基于标题）
        seen = set()
        unique_notes = []
        for note in all_notes:
            key = note.get("title", "").lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique_notes.append(note)
        
        logger.info(f"[XHS Topic] Total unique notes from all topics: {len(unique_notes)}")
        return unique_notes


# 全局客户端
_xhs_topic_client: Optional[XHSTopicClient] = None


def get_xhs_topic_client() -> XHSTopicClient:
    """获取全局客户端"""
    global _xhs_topic_client
    if _xhs_topic_client is None:
        _xhs_topic_client = XHSTopicClient()
    return _xhs_topic_client


async def get_xhs_topic_notes(limit_per_topic: int = 5) -> List[Dict[str, Any]]:
    """便捷函数：获取话题笔记"""
    client = get_xhs_topic_client()
    return await client.fetch_all_topics_feed(limit_per_topic=limit_per_topic)
