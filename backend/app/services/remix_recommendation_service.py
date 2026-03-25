"""
仿写推荐：结合 IP 定位关键词 + 抖音低粉爆款榜 + 小红书话题笔记流（TikHub）。
strategy_config.remix 可配置：
  search_keywords: 额外关键词列表
  xhs_topic_page_ids: 小红书话题 page_id 列表
环境变量：TIKHUB_XHS_TOPIC_PAGE_IDS、TIKHUB_REMIX_EXTRA_KEYWORDS（逗号分隔）
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.db.models import IP
from app.services import tikhub_client

logger = logging.getLogger(__name__)


def _split_keywords(text: str) -> List[str]:
    parts = re.split(r"[,，、\s]+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) >= 2]


def keywords_from_ip(ip: IP) -> List[str]:
    words: List[str] = []
    for field in (
        ip.expertise,
        ip.content_direction,
        ip.target_audience,
        ip.passion,
        ip.market_demand,
        ip.unique_value_prop,
        ip.nickname,
        ip.bio,
        ip.product_service,
    ):
        if field and isinstance(field, str):
            words.extend(_split_keywords(field))

    sc = ip.strategy_config if isinstance(ip.strategy_config, dict) else {}
    remix = sc.get("remix") if isinstance(sc, dict) else {}
    if isinstance(remix, dict):
        for k in remix.get("search_keywords") or []:
            if isinstance(k, str) and k.strip():
                words.append(k.strip())

    extra = os.environ.get("TIKHUB_REMIX_EXTRA_KEYWORDS", "").strip()
    if extra:
        for x in extra.split(","):
            x = x.strip()
            if len(x) >= 2:
                words.append(x)

    seen: set = set()
    out: List[str] = []
    for w in words:
        lw = w.lower()
        if lw in seen:
            continue
        seen.add(lw)
        out.append(w)
    return out[:40]


def _match_score(title: str, keywords: List[str]) -> int:
    if not title or not keywords:
        return 0
    t = title.lower()
    return sum(1 for k in keywords if k.lower() in t)


def _xhs_topic_page_ids_for_ip(ip: IP) -> List[str]:
    ids: List[str] = []
    sc = ip.strategy_config if isinstance(ip.strategy_config, dict) else {}
    remix = sc.get("remix") if isinstance(sc, dict) else {}
    if isinstance(remix, dict):
        for pid in remix.get("xhs_topic_page_ids") or []:
            if isinstance(pid, str) and pid.strip():
                ids.append(pid.strip())
    env_ids = os.environ.get("TIKHUB_XHS_TOPIC_PAGE_IDS", "").strip()
    if env_ids:
        for x in env_ids.split(","):
            x = x.strip()
            if x and x not in ids:
                ids.append(x)
    return ids


async def build_remix_recommendations(
    db: Session,
    ip_id: str,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        return []
    kws = keywords_from_ip(ip)
    items: List[Dict[str, Any]] = []
    seen_urls: set = set()

    if tikhub_client.is_configured():
        try:
            raw = await tikhub_client.fetch_douyin_low_fan_hot_list(
                page=1, page_size=40, date_window=2
            )
            parsed = tikhub_client.parse_low_fan_explosion_items(raw)
            scored: List[Dict[str, Any]] = []
            for p in parsed:
                title = p.get("title") or ""
                m = _match_score(title, kws)
                scored.append({**p, "_match": m})
            scored.sort(key=lambda x: (-x["_match"], x.get("title") or ""))
            for p in scored:
                u = (p.get("url") or "").strip()
                if not u or u in seen_urls:
                    continue
                seen_urls.add(u)
                reason = "抖音低粉爆款榜"
                if kws and p["_match"] > 0:
                    reason = f"与IP方向匹配 · 低粉爆款（命中 {p['_match']} 个关键词）"
                items.append(
                    {
                        "url": u,
                        "title": p.get("title") or "未命名",
                        "platform": "douyin",
                        "reason": reason,
                    }
                )
                if len(items) >= limit:
                    return items[:limit]
        except Exception as e:
            logger.warning("抖音低粉爆款榜拉取失败: %s", e)

    for page_id in _xhs_topic_page_ids_for_ip(ip):
        if len(items) >= limit:
            break
        topic_name = ""
        try:
            info = await tikhub_client.fetch_xhs_topic_info(page_id)
            topic_name = tikhub_client.topic_display_name_from_xhs_info(info) or page_id
        except Exception as e:
            logger.warning("小红书话题详情失败 page_id=%s: %s", page_id, e)
            topic_name = page_id
        try:
            feed = await tikhub_client.fetch_xhs_topic_feed(page_id, sort="trend")
            notes = tikhub_client.parse_xhs_topic_feed_notes(
                feed, topic_label=topic_name
            )
            for n in notes:
                u = (n.get("url") or "").strip()
                if not u or u in seen_urls:
                    continue
                seen_urls.add(u)
                title = n.get("title") or "小红书笔记"
                m = _match_score(title, kws)
                label = n.get("topic_name") or topic_name
                reason = f"小红书话题「{label[:32]}」"
                if kws and m > 0:
                    reason = f"与IP方向匹配 · {reason}"
                items.append(
                    {
                        "url": u,
                        "title": title,
                        "platform": "xiaohongshu",
                        "reason": reason,
                    }
                )
                if len(items) >= limit:
                    break
        except Exception as e:
            logger.warning("小红书话题笔记流失败 page_id=%s: %s", page_id, e)

    return items[:limit]
