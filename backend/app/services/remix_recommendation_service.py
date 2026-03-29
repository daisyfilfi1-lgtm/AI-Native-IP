"""
仿写推荐：优先显示竞品爆款视频直链（competitor_videos 或 TikHub 按 sec_uid 拉取）
  + 抖音低粉爆款榜（TikHub）+ 小红书话题笔记。
strategy_config.remix 可配置：
  search_keywords: 额外关键词列表
  xhs_topic_page_ids: 小红书话题 page_id 列表
环境变量：TIKHUB_XHS_TOPIC_PAGE_IDS、TIKHUB_REMIX_EXTRA_KEYWORDS（逗号分隔）
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import IP
from app.services import tikhub_client
from app.services.competitor_client import get_competitor_client

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


def keywords_from_env_only() -> List[str]:
    """无 IP 记录时仅用 TIKHUB_REMIX_EXTRA_KEYWORDS 等环境变量做标题匹配。"""
    words: List[str] = []
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


def remix_keywords_for_ip(ip: Optional[IP]) -> List[str]:
    if ip is None:
        return keywords_from_env_only()
    return keywords_from_ip(ip)


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


def _xhs_topic_page_ids_env_only() -> List[str]:
    ids: List[str] = []
    env_ids = os.environ.get("TIKHUB_XHS_TOPIC_PAGE_IDS", "").strip()
    if env_ids:
        for x in env_ids.split(","):
            x = x.strip()
            if x and x not in ids:
                ids.append(x)
    return ids


def _xhs_topic_page_ids_for_remix(ip: Optional[IP]) -> List[str]:
    if ip is None:
        return _xhs_topic_page_ids_env_only()
    return _xhs_topic_page_ids_for_ip(ip)


_URL_IN_TEXT_RE = re.compile(r"https?://[^\s\)\]\"'<>]+", re.IGNORECASE)


def _extract_http_urls(text: Optional[str]) -> List[str]:
    if not text or not isinstance(text, str):
        return []
    out: List[str] = []
    for m in _URL_IN_TEXT_RE.finditer(text.strip()):
        u = m.group(0).rstrip(".,;，。；、")
        if u and u not in out:
            out.append(u)
    return out


def _platform_lower(p: Optional[str]) -> str:
    return (p or "").strip().lower()


def _is_video_content_url(url: str) -> bool:
    """仅接受可仿写的单条视频/笔记链接，排除主页、用户页。"""
    u = (url or "").strip().lower()
    if not u.startswith("http"):
        return False
    if "douyin.com/user" in u:
        return False
    if "xiaohongshu.com/user/" in u:
        return False
    if "douyin.com/video/" in u or "v.douyin.com" in u:
        return True
    if "xiaohongshu.com/explore/" in u:
        return True
    if "xhslink.com" in u:
        return True
    if "xiaohongshu.com/discovery/item" in u:
        return True
    if "channels.weixin.qq.com" in u and "/video/" in u:
        return True
    return False


async def _best_douyin_video_item_from_sec_uid(
    sec_uid: str, competitor_name: str
) -> Optional[Dict[str, Any]]:
    """按 sec_uid 拉取近期作品，取点赞最高的一条作为爆款视频链接。"""
    uid = (sec_uid or "").strip()
    if not uid:
        return None
    client = get_competitor_client()
    if not (client.api_key or "").strip():
        return None
    try:
        videos = await client.fetch_user_videos(uid, count=20)
    except Exception as e:
        logger.warning("按 sec_uid 拉取竞品视频失败: %s", e)
        return None
    if not videos:
        return None
    best = max(videos, key=lambda x: int(x.get("digg_count") or 0))
    url = (best.get("sourceUrl") or "").strip()
    if not url or not _is_video_content_url(url):
        return None
    title = (best.get("title") or best.get("originalTitle") or "视频")[:200]
    digg = int(best.get("digg_count") or 0)
    like_str = f"{digg / 10000:.1f}万" if digg > 10000 else str(digg)
    return {
        "url": url,
        "title": title,
        "platform": "douyin",
        "reason": f"我的竞品：{competitor_name} · {like_str}赞",
        "is_my_competitor": True,
        "competitor_name": competitor_name,
        "like_count": digg,
    }


async def build_remix_recommendations(
    db: Session,
    ip_id: str,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    from sqlalchemy import text
    
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    kws = remix_keywords_for_ip(ip)
    items: List[Dict[str, Any]] = []
    seen_urls: set = set()
    competitors_with_video: set = set()
    
    # 首先获取已抓取的竞品视频（按点赞数排序，优先显示爆款）
    try:
        # 直接查询 competitor_videos 表
        result = db.execute(text("""
            SELECT v.competitor_id, v.video_id, v.title, v.author, v.platform, v.like_count, v.play_count, c.name as competitor_name
            FROM competitor_videos v
            JOIN competitor_accounts c ON v.competitor_id = c.competitor_id
            WHERE c.ip_id = :ip_id
            ORDER BY v.like_count DESC NULLS LAST
            LIMIT :limit
        """), {"ip_id": ip_id, "limit": limit})
        
        videos = result.fetchall()
        for video in videos:
            competitors_with_video.add(video.competitor_id)
            platform = video.platform or "douyin"
            video_id = video.video_id
            
            # 构造视频链接
            if platform == "douyin":
                video_url = f"https://www.douyin.com/video/{video_id}"
            elif platform == "xiaohongshu":
                video_url = f"https://www.xiaohongshu.com/explore/{video_id}"
            else:
                continue
            
            if video_url in seen_urls:
                continue
            seen_urls.add(video_url)
            
            # 构造理由文本
            like_str = f"{video.like_count / 10000:.1f}万" if video.like_count and video.like_count > 10000 else str(video.like_count or 0)
            reason = f"我的竞品：{video.competitor_name} · {like_str}赞"
            
            items.append({
                "url": video_url,
                "title": video.title or f"{video.author}的视频",
                "platform": platform,
                "reason": reason,
                "is_my_competitor": True,
                "competitor_name": video.competitor_name,
                "like_count": video.like_count,
            })
            
            if len(items) >= limit:
                return items[:limit]
                
    except Exception as e:
        logger.warning("已抓取竞品视频加载失败: %s", e)

    # 库中无该账号视频时：优先备注里的单条视频链接，否则用抖音 sec_uid 实时拉取点赞最高的一条（不要主页链接）
    if len(items) < limit:
        try:
            acc_rows = db.execute(
                text("""
                    SELECT competitor_id, name, platform, external_id, notes
                    FROM competitor_accounts
                    WHERE ip_id = :ip_id
                    ORDER BY updated_at DESC NULLS LAST, created_at DESC
                """),
                {"ip_id": ip_id},
            ).fetchall()
            for row in acc_rows:
                if len(items) >= limit:
                    break
                cid = row.competitor_id
                if cid in competitors_with_video:
                    continue
                name = row.name or "竞品"
                plat = row.platform or "douyin"
                notes = row.notes or ""
                pl = _platform_lower(plat)

                picked: Optional[Dict[str, Any]] = None
                for u in _extract_http_urls(notes):
                    if _is_video_content_url(u):
                        host = u.lower()
                        item_plat = (
                            "xiaohongshu"
                            if ("xiaohongshu.com" in host or "xhslink.com" in host)
                            else "douyin"
                        )
                        picked = {
                            "url": u,
                            "title": f"{name} · 备注中的爆款视频",
                            "platform": item_plat,
                            "reason": f"我的竞品监控账号（备注中的视频链接）",
                            "is_my_competitor": True,
                            "competitor_name": name,
                        }
                        break
                if picked is None and pl in ("douyin", "dy", "抖音") and (row.external_id or "").strip():
                    picked = await _best_douyin_video_item_from_sec_uid(row.external_id, name)

                if picked and (picked.get("url") or "").strip() not in seen_urls:
                    u = picked["url"].strip()
                    seen_urls.add(u)
                    items.append(picked)
        except Exception as e:
            logger.warning("竞品账号视频链接补充失败: %s", e)

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
                    label = "关键词配置" if ip is None else "IP方向"
                    reason = f"与{label}匹配 · 低粉爆款（命中 {p['_match']} 个关键词）"
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

    for page_id in _xhs_topic_page_ids_for_remix(ip):
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
                    lbl = "关键词配置" if ip is None else "IP方向"
                    reason = f"与{lbl}匹配 · {reason}"
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
