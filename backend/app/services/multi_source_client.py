"""
多数据源聚合客户端
支持：小红书、快手、抖音、微博等平台的热点聚合
为小敏IP（宝妈创业/花样馒头）定制数据源权重
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.services import tikhub_client, xhs_topic_client, competitor_client

logger = logging.getLogger(__name__)

# 数据源权重配置（针对小敏IP优化）
# 小红书：女性用户多，宝妈群体活跃，最相关
# 快手：下沉市场，宝妈用户多，相关度高
# 抖音：短视频平台，通用
# 微博：大众热点，相关性较低
SOURCE_WEIGHTS = {
    "xiaohongshu": 1.5,  # 小红书 - 最高权重（女性/宝妈聚集）
    "kuaishou": 1.3,     # 快手 - 高权重（下沉市场/宝妈多）
    "douyin": 1.0,       # 抖音 - 标准权重
    "weibo": 0.6,        # 微博 - 低权重（太泛）
}

# 平台标签映射
PLATFORM_TAGS = {
    "xiaohongshu": "小红书",
    "kuaishou": "快手",
    "douyin": "抖音",
    "weibo": "微博",
}


class MultiSourceClient:
    """多数据源聚合客户端"""
    
    def __init__(self):
        self.api_key = os.environ.get("TIKHUB_API_KEY", "").strip()
        self.base_url = os.environ.get("TIKHUB_BASE_URL", "https://api.tikhub.io")
        self.enabled_sources = self._get_enabled_sources()
    
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    def _get_enabled_sources(self) -> List[str]:
        """获取启用的数据源列表"""
        # 从环境变量读取，默认启用小红书和快手
        sources_str = os.environ.get("TIKHUB_SOURCES", "xiaohongshu,kuaishou,douyin")
        return [s.strip() for s in sources_str.split(",") if s.strip()]
    
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
                logger.warning(f"[MultiSource] HTTP {r.status_code}: {body}")
                return {}
            return body
    
    async def fetch_xiaohongshu_hot_list(self, limit: int = 12) -> List[Dict[str, Any]]:
        """
        获取小红书热榜
        GET /api/v1/xiaohongshu/web_v2/fetch_hot_list
        """
        try:
            logger.info("[MultiSource] Fetching Xiaohongshu hot list...")
            resp = await self._request(
                "GET",
                "/api/v1/xiaohongshu/web_v2/fetch_hot_list",
                params={"limit": limit}
            )
            
            # 解析响应
            data = resp.get("data") if isinstance(resp, dict) else resp
            if not data:
                logger.warning("[MultiSource] Xiaohongshu: empty response")
                return []
            
            # 小红书数据结构：data.data.items
            items = []
            if isinstance(data, dict):
                inner_data = data.get("data", {})
                if isinstance(inner_data, dict):
                    items = inner_data.get("items", [])
            elif isinstance(data, list):
                items = data
            
            cards = []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                title = item.get("title") or item.get("word") or ""
                if not title:
                    continue
                
                cards.append({
                    "id": f"xhs_{len(cards)+1}",
                    "title": title,
                    "originalTitle": title,
                    "score": 4.5 + min(0.45, len(cards) * 0.03),
                    "tags": ["小红书", "热榜"],
                    "reason": "小红书热榜（女性/宝妈聚集）",
                    "estimatedViews": "—",
                    "estimatedCompletion": 0,
                    "sourceUrl": item.get("link") or "",
                    "platform": "xiaohongshu",
                    "weight": SOURCE_WEIGHTS["xiaohongshu"],
                })
            
            logger.info(f"[MultiSource] Xiaohongshu: {len(cards)} cards")
            return cards
            
        except Exception as e:
            logger.error(f"[MultiSource] Xiaohongshu error: {e}")
            return []
    
    async def fetch_kuaishou_hot_list(self, limit: int = 12) -> List[Dict[str, Any]]:
        """
        获取快手热榜
        GET /api/v1/kuaishou/web/fetch_hot_list
        """
        try:
            logger.info("[MultiSource] Fetching Kuaishou hot list...")
            resp = await self._request(
                "GET",
                "/api/v1/kuaishou/web/fetch_hot_list",
                params={"limit": limit}
            )
            
            data = resp.get("data") if isinstance(resp, dict) else resp
            if not data:
                logger.warning("[MultiSource] Kuaishou: empty response")
                return []
            
            items = data if isinstance(data, list) else data.get("list", [])
            
            cards = []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                title = item.get("title") or item.get("name") or ""
                if not title:
                    continue
                
                cards.append({
                    "id": f"ks_{len(cards)+1}",
                    "title": title,
                    "originalTitle": title,
                    "score": 4.5 + min(0.45, len(cards) * 0.03),
                    "tags": ["快手", "热榜"],
                    "reason": "快手热榜（下沉市场/宝妈多）",
                    "estimatedViews": "—",
                    "estimatedCompletion": 0,
                    "sourceUrl": item.get("url") or "",
                    "platform": "kuaishou",
                    "weight": SOURCE_WEIGHTS["kuaishou"],
                })
            
            logger.info(f"[MultiSource] Kuaishou: {len(cards)} cards")
            return cards
            
        except Exception as e:
            logger.error(f"[MultiSource] Kuaishou error: {e}")
            return []
    
    async def fetch_douyin_hot_list(self, limit: int = 12) -> List[Dict[str, Any]]:
        """
        获取抖音热榜（高播榜）
        复用现有的 tikhub_client
        """
        try:
            logger.info("[MultiSource] Fetching Douyin hot list...")
            
            # 使用现有的 tikhub_client
            raw = await tikhub_client.fetch_douyin_high_play_hot_list(
                page=1, page_size=max(limit, 5)
            )
            
            cards = tikhub_client.billboard_to_topic_cards(raw, limit=limit)
            
            # 添加平台标识和权重
            for card in cards:
                card["id"] = f"dy_{card.get('id', len(cards))}"
                card["platform"] = "douyin"
                card["weight"] = SOURCE_WEIGHTS["douyin"]
            
            logger.info(f"[MultiSource] Douyin: {len(cards)} cards")
            return cards
            
        except Exception as e:
            logger.error(f"[MultiSource] Douyin error: {e}")
            return []
    
    async def fetch_all_sources(self, limit: int = 12) -> List[Dict[str, Any]]:
        """
        并发获取所有数据源
        返回聚合后的热点列表
        """
        if not self.is_configured():
            logger.warning("[MultiSource] API key not configured")
            return []
        
        # 定义数据源任务
        tasks = []
        source_names = []
        
        if "xiaohongshu" in self.enabled_sources:
            tasks.append(self.fetch_xiaohongshu_hot_list(limit))
            source_names.append("xiaohongshu")
        
        if "kuaishou" in self.enabled_sources:
            tasks.append(self.fetch_kuaishou_hot_list(limit))
            source_names.append("kuaishou")
        
        if "douyin" in self.enabled_sources:
            tasks.append(self.fetch_douyin_hot_list(limit))
            source_names.append("douyin")
        
        # 并发执行热榜数据源
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集热榜结果
        all_cards: List[Dict[str, Any]] = []
        for name, result in zip(source_names, results):
            if isinstance(result, Exception):
                logger.error(f"[MultiSource] {name} failed: {result}")
                continue
            if result:
                all_cards.extend(result)
                logger.info(f"[MultiSource] {name}: added {len(result)} cards")
        
        # 额外获取小红书话题标签笔记（更精准）
        try:
            xhs_topic_notes = await xhs_topic_client.get_xhs_topic_notes(limit_per_topic=5)
            if xhs_topic_notes:
                # 给话题标签笔记更高权重
                for note in xhs_topic_notes:
                    note["weight"] = 2.0  # 话题标签笔记权重最高
                    note["reason"] = "小红书话题标签（精准竞品）"
                all_cards.extend(xhs_topic_notes)
                logger.info(f"[MultiSource] XHS Topic: added {len(xhs_topic_notes)} notes")
        except Exception as e:
            logger.warning(f"[MultiSource] XHS Topic failed: {e}")
        
        # 额外获取竞品抖音账号视频（最精准）
        try:
            competitor_videos = await competitor_client.get_competitor_videos(count_per_user=5)
            if competitor_videos:
                all_cards.extend(competitor_videos)
                logger.info(f"[MultiSource] Competitor: added {len(competitor_videos)} videos")
        except Exception as e:
            logger.warning(f"[MultiSource] Competitor failed: {e}")
        
        logger.info(f"[MultiSource] Total cards from all sources: {len(all_cards)}")
        return all_cards
    
    async def get_aggregated_topics(self, limit: int = 12) -> List[Dict[str, Any]]:
        """
        获取聚合后的热点话题
        按权重排序，去重
        """
        cards = await self.fetch_all_sources(limit * 2)  # 获取更多用于筛选
        
        if not cards:
            return []
        
        # 按权重排序
        sorted_cards = sorted(
            cards,
            key=lambda x: float(x.get("score", 0)) * float(x.get("weight", 1.0)),
            reverse=True
        )
        
        # 去重（基于标题相似度）
        unique_cards = []
        seen_titles: set = set()
        
        for card in sorted_cards:
            title = str(card.get("title", "")).lower().strip()
            # 简单去重：检查是否包含已有关键词
            is_duplicate = any(title in seen or seen in title for seen in seen_titles)
            if not is_duplicate and title:
                seen_titles.add(title)
                unique_cards.append(card)
                if len(unique_cards) >= limit:
                    break
        
        logger.info(f"[MultiSource] Aggregated {len(unique_cards)} unique topics")
        return unique_cards


# 全局客户端实例
_multi_source_client: Optional[MultiSourceClient] = None


def get_multi_source_client() -> MultiSourceClient:
    """获取全局多数据源客户端"""
    global _multi_source_client
    if _multi_source_client is None:
        _multi_source_client = MultiSourceClient()
    return _multi_source_client


async def get_multi_source_topics(limit: int = 12) -> List[Dict[str, Any]]:
    """便捷函数：获取多数据源聚合话题"""
    client = get_multi_source_client()
    return await client.get_aggregated_topics(limit=limit)
