"""
TikHub API 客户端（推荐选题：抖音热榜；仿写：混合解析单条链接）。
文档：https://docs.tikhub.io/  · 环境变量：TIKHUB_API_KEY、TIKHUB_BASE_URL
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE = "https://api.tikhub.io"


class TikHubError(Exception):
    """TikHub 返回业务错误或 HTTP 错误"""


def is_configured() -> bool:
    return bool(os.environ.get("TIKHUB_API_KEY", "").strip())


def _base_url() -> str:
    return os.environ.get("TIKHUB_BASE_URL", DEFAULT_BASE).strip().rstrip("/")


def _headers() -> Dict[str, str]:
    key = os.environ.get("TIKHUB_API_KEY", "").strip()
    if not key:
        raise TikHubError("TIKHUB_API_KEY 未配置")
    return {"Authorization": f"Bearer {key}"}


def unwrap_response(resp: Dict[str, Any]) -> Any:
    """解析 TikHub 统一外壳：code、data（可能为 JSON 字符串）"""
    if not isinstance(resp, dict):
        return resp
    code = resp.get("code")
    if code is not None:
        try:
            c = int(code)
        except (TypeError, ValueError):
            c = -1
        # TikHub 常见成功码为 0（部分接口可能返回 200）；其余视为业务失败。
        if c not in (0, 200):
            msg = resp.get("message_zh") or resp.get("message") or str(resp)
            raise TikHubError(msg)
    data = resp.get("data")
    if isinstance(data, str):
        s = data.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return data
    # 部分 TikHub 接口会在 data 内再包一层 code/message
    if isinstance(data, dict) and "code" in data:
        try:
            inner_code = int(data.get("code"))
        except (TypeError, ValueError):
            inner_code = -1
        if inner_code not in (0, 200):
            msg = data.get("message_zh") or data.get("message") or str(data)
            raise TikHubError(msg)
    return data


async def _request(method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    url = f"{_base_url()}{path}"
    timeout = httpx.Timeout(60.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.request(method, url, headers=_headers(), **kwargs)
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}
        if r.status_code >= 400:
            raise TikHubError(f"HTTP {r.status_code}: {body}")
        if not isinstance(body, dict):
            raise TikHubError("响应格式异常")
        return body


async def hybrid_video_data(url: str) -> Any:
    """
    混合解析单一视频（抖音/TikTok 分享链等）。
    GET /api/v1/hybrid/video_data?url=...
    """
    return unwrap_response(
        await _request(
            "GET",
            "/api/v1/hybrid/video_data",
            params={"url": url.strip(), "minimal": False},
        )
    )


async def fetch_douyin_web_one_video_by_share_url(share_url: str) -> Any:
    """
    抖音 Web：根据分享链获取单条作品。
    GET /api/v1/douyin/web/fetch_one_video_by_share_url?share_url=...
    """
    return unwrap_response(
        await _request(
            "GET",
            "/api/v1/douyin/web/fetch_one_video_by_share_url",
            params={"share_url": share_url.strip()},
        )
    )


async def fetch_douyin_low_fan_hot_list(
    page: int = 1,
    page_size: int = 20,
    date_window: int = 2,
) -> Any:
    """
    抖音热榜 · 低粉爆款榜（用于仿写推荐）。
    POST /api/v1/douyin/billboard/fetch_hot_total_low_fan_list
    """
    payload = {
        "page": page,
        "page_size": page_size,
        "date_window": date_window,
        "tags": [],
    }
    return unwrap_response(
        await _request(
            "POST",
            "/api/v1/douyin/billboard/fetch_hot_total_low_fan_list",
            json=payload,
        )
    )


async def fetch_xhs_topic_info(page_id: str, source: str = "normal") -> Any:
    """GET /api/v1/xiaohongshu/app_v2/get_topic_info"""
    return unwrap_response(
        await _request(
            "GET",
            "/api/v1/xiaohongshu/app_v2/get_topic_info",
            params={"page_id": page_id.strip(), "source": source},
        )
    )


async def fetch_xhs_topic_feed(
    page_id: str,
    sort: str = "trend",
    **extra: Any,
) -> Any:
    """GET /api/v1/xiaohongshu/app_v2/get_topic_feed"""
    params: Dict[str, Any] = {"page_id": page_id.strip(), "sort": sort}
    for k in (
        "cursor_score",
        "last_note_id",
        "last_note_ct",
        "session_id",
        "first_load_time",
        "source",
    ):
        if k in extra and extra[k] not in (None, ""):
            params[k] = extra[k]
    return unwrap_response(
        await _request(
            "GET",
            "/api/v1/xiaohongshu/app_v2/get_topic_feed",
            params=params,
        )
    )


def looks_like_douyin_share_url(url: str) -> bool:
    u = url.lower()
    return "douyin.com" in u or "iesdouyin.com" in u


def extract_douyin_video_url(data: Any) -> Optional[str]:
    """
    从 TikHub 抖音单条作品响应中提取无水印视频地址。
    优先取 video.play_addr.url_list[0]，其次 video.play_addr_lowbr.url_list[0]。
    """
    if not isinstance(data, dict):
        return None

    # 解包 TikHub 常见嵌套
    for key in ("aweme_detail", "aweme", "video", "item", "data"):
        if key in data and isinstance(data[key], dict):
            data = {**data, **data[key]}

    video = data.get("video")
    if not isinstance(video, dict):
        return None

    for addr_key in ("play_addr", "play_addr_lowbr"):
        addr = video.get(addr_key)
        if isinstance(addr, dict):
            url_list = addr.get("url_list")
            if isinstance(url_list, list):
                for u in url_list:
                    if isinstance(u, str) and u.startswith("http"):
                        return u
    return None


_URL_RE = re.compile(r"https?://[^\s<>\"']+")
_GENERIC_TOPIC_TITLE_RE = re.compile(r"^热点选题\s*\d+$")


def collect_http_urls(obj: Any) -> List[str]:
    found: List[str] = []

    def walk(x: Any) -> None:
        if isinstance(x, str):
            found.extend(_URL_RE.findall(x))
        elif isinstance(x, dict):
            for k, v in x.items():
                lk = str(k).lower()
                if lk in (
                    "share_url",
                    "shareurl",
                    "video_url",
                    "url",
                    "link",
                    "note_url",
                    "note_share_url",
                ) and isinstance(v, str) and v.startswith("http"):
                    found.append(v.strip())
                walk(v)
        elif isinstance(x, list):
            for it in x:
                walk(it)

    walk(obj)
    # 去重保序
    return list(dict.fromkeys(found))


def _pick_douyin_url(urls: List[str]) -> Optional[str]:
    for u in urls:
        if looks_like_douyin_share_url(u):
            return u
    return urls[0] if urls else None


def _pick_xhs_url(urls: List[str]) -> Optional[str]:
    for u in urls:
        lu = u.lower()
        if "xiaohongshu.com" in lu or "xhslink" in lu or "xhscdn" in lu:
            return u
    return urls[0] if urls else None


def parse_low_fan_explosion_items(data: Any) -> List[Dict[str, Any]]:
    """从低粉爆款榜响应中解析 {title, url} 列表"""
    items: List[Any] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for k in ("list", "data", "items", "records", "aweme_list", "hot_list"):
            v = data.get(k)
            if isinstance(v, list):
                items = v
                break
        if not items:
            items = [data]

    out: List[Dict[str, Any]] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = _title_from_item(item, i)
        urls = collect_http_urls(item)
        u = _pick_douyin_url(urls)
        if u:
            out.append({"title": title, "url": u})
    return out


def topic_display_name_from_xhs_info(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    for root in (data.get("page_info"), data.get("topic_info"), data):
        if isinstance(root, dict):
            for k in ("name", "title", "topic_name", "page_title"):
                v = root.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()[:80]
    return ""


def parse_xhs_topic_feed_notes(
    data: Any,
    topic_label: str = "",
) -> List[Dict[str, Any]]:
    """从话题笔记流中解析 {title, url, topic_name}"""
    items: List[Any] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for k in ("items", "notes", "list", "data", "records"):
            v = data.get(k)
            if isinstance(v, list):
                items = v
                break
    topic_name = topic_label
    if isinstance(data, dict) and not topic_name:
        pi = data.get("page_info")
        if isinstance(pi, dict):
            n = pi.get("name") or pi.get("title")
            if isinstance(n, str):
                topic_name = n.strip()[:80]

    out: List[Dict[str, Any]] = []
    for i, note in enumerate(items):
        if not isinstance(note, dict):
            continue
        title = _title_from_item(note, i)
        urls = collect_http_urls(note)
        u = _pick_xhs_url(urls)
        if u:
            out.append({"title": title, "url": u, "topic_name": topic_name or topic_label})
    return out


async def resolve_share_url_for_tikhub(url: str) -> str:
    """
    小红书短链（xhslink.com）常带 http，需 https + 跟随跳转，hybrid 接口才易解析成功。
    """
    u = (url or "").strip()
    if not u:
        return u
    if u.startswith("http://"):
        u = "https://" + u[len("http://") :]
    low = u.lower()
    if "xhslink.com" not in low:
        return u
    try:
        timeout = httpx.Timeout(25.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(
                u,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
            )
            final = str(r.url)
            if final.startswith("http"):
                return final.split("#")[0]
    except Exception as e:
        logger.warning("resolve_share_url_for_tikhub failed url=%s: %s", url[:120], e)
    return u


async def try_extract_competitor_text_tikhub(resolved_url: str) -> Optional[str]:
    """
    仿写解构用文本：抖音分享链优先走 Web 单条作品接口，其余走 hybrid。
    成功返回非空字符串；未配置或解析失败返回 None（由上层决定是否换源或退回 URL）。
    """
    u = (resolved_url or "").strip()
    if not u:
        return None
    if not is_configured():
        return None
    if looks_like_douyin_share_url(u):
        try:
            raw = await fetch_douyin_web_one_video_by_share_url(u)
            extracted = extract_video_text_for_remix(raw)
            if extracted.strip():
                return extracted
        except Exception as e:
            logger.warning("Douyin Web 单条解析失败，回退 hybrid: %s", e)
    try:
        raw = await hybrid_video_data(u)
        out = extract_video_text_for_remix(raw)
        return out if (out or "").strip() else None
    except Exception as e:
        logger.warning("TikHub hybrid 解析失败: %s", e)
        return None


async def fetch_douyin_high_play_hot_list(
    page: int = 1,
    page_size: int = 12,
    date_window: int = 1,  # 修改为 1，TikHub 高播榜只接受 date_window=1
) -> Any:
    """
    抖音热榜 · 高播榜（用于推荐选题）。
    POST /api/v1/douyin/billboard/fetch_hot_total_high_play_list
    """
    payload = {
        "page": page,
        "page_size": page_size,
        "date_window": date_window,
        "tags": [],
    }
    return unwrap_response(
        await _request(
            "POST",
            "/api/v1/douyin/billboard/fetch_hot_total_high_play_list",
            json=payload,
        )
    )


def _walk_strings(obj: Any, key_hint: str) -> List[str]:
    out: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if key_hint in lk and isinstance(v, str) and v.strip():
                out.append(v.strip())
            else:
                out.extend(_walk_strings(v, key_hint))
    elif isinstance(obj, list):
        for it in obj:
            out.extend(_walk_strings(it, key_hint))
    return out


def extract_video_text_for_remix(data: Any) -> str:
    """从 hybrid 返回结构中抽出可用作文案解构的文本"""
    if data is None:
        return ""
    if isinstance(data, str):
        return data.strip()[:12000]
    if not isinstance(data, dict):
        return str(data)[:12000]

    parts: List[str] = []
    for key in ("desc", "title", "share_title", "video_title", "text"):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())

    nested_keys = ("aweme_detail", "aweme", "video", "item", "data")
    for nk in nested_keys:
        sub = data.get(nk)
        if isinstance(sub, dict):
            inner = extract_video_text_for_remix(sub)
            if inner:
                parts.append(inner)

    if not parts:
        titles = _walk_strings(data, "title")
        descs = _walk_strings(data, "desc")
        parts.extend(titles[:3])
        parts.extend(descs[:3])

    text = "\n\n".join(dict.fromkeys(p for p in parts if p))
    return text[:12000]


def _get_nested_str(item: Any, key: str) -> Optional[str]:
    """从嵌套字典中获取字符串值"""
    if not isinstance(item, dict):
        return None
    val = item.get(key)
    if isinstance(val, str) and val.strip():
        return val.strip()
    # 尝试从嵌套结构获取
    for nested_key in ("aweme_detail", "video", "item", "data"):
        nested = item.get(nested_key)
        if isinstance(nested, dict):
            nested_val = nested.get(key)
            if isinstance(nested_val, str) and nested_val.strip():
                return nested_val.strip()
    return None


def _score_from_item(item: Any, idx: int) -> float:
    if not isinstance(item, dict):
        return round(4.5 + min(0.45, idx * 0.02), 2)
    for k in ("hot_score", "score", "heat", "play_count", "play_cnt"):
        v = item.get(k)
        if isinstance(v, (int, float)) and v > 0:
            return round(min(4.95, 4.0 + min(0.95, (float(v) % 1000) / 1000)), 2)
    return round(4.85 - min(0.35, idx * 0.03), 2)


def _title_from_item(item: Any, idx: int) -> str:
    def _clean_title(v: Any) -> str:
        if not isinstance(v, str):
            return ""
        s = v.strip()[:200]
        if not s:
            return ""
        if _GENERIC_TOPIC_TITLE_RE.match(s):
            return ""
        return s

    if isinstance(item, str) and item.strip():
        return _clean_title(item)
    if isinstance(item, dict):
        for k in (
            "title",
            "sentence",
            "word",
            "hot_word",
            "item_title",
            "challenge_name",
            "desc",
        ):
            s = _clean_title(item.get(k))
            if s:
                return s
        for k in ("aweme_info", "aweme", "video"):
            sub = item.get(k)
            if isinstance(sub, dict):
                t = _title_from_item(sub, idx)
                if t:
                    return t
    return ""


def _tags_from_item(item: Any) -> List[str]:
    tags: List[str] = []
    if isinstance(item, dict):
        for k in ("sentence_tag", "category", "tag", "label"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                tags.append(v.strip()[:20])
            elif isinstance(v, list):
                for x in v[:3]:
                    if isinstance(x, str) and x.strip():
                        tags.append(x.strip()[:20])
    return tags[:4]


def _play_count_from_billboard_item(item: Any) -> int:
    """从热榜单条结构中解析播放量（抖音 statistics.play_count 等）。"""
    if not isinstance(item, dict):
        return 0

    def _from_stats(obj: Any) -> int:
        if not isinstance(obj, dict):
            return 0
        st = obj.get("statistics")
        if isinstance(st, dict):
            for k in ("play_count", "play_cnt", "read_count"):
                v = st.get(k)
                if isinstance(v, (int, float)) and v > 0:
                    return int(v)
        for k in ("play_count", "play_cnt"):
            v = obj.get(k)
            if isinstance(v, (int, float)) and v > 0:
                return int(v)
        return 0

    pc = _from_stats(item)
    if pc:
        return pc
    for key in ("aweme_detail", "video", "item", "data"):
        sub = item.get(key)
        if isinstance(sub, dict):
            pc = _from_stats(sub)
            if pc:
                return pc
    return 0


def _format_views_for_topic_card(pc: int) -> str:
    if pc <= 0:
        return "—"
    if pc >= 1000000:
        return f"{pc / 10000:.0f}万+"
    if pc >= 10000:
        return f"{pc / 10000:.1f}万"
    if pc >= 1000:
        return f"{pc / 1000:.1f}千"
    return str(pc)


def _completion_from_play_count(pc: int) -> int:
    """有播放量时用对数映射到预估完播率区间，避免与无数据时全是 35% 雷同。"""
    if pc <= 0:
        return 35
    return min(92, max(24, int(26 + math.log10(pc + 1) * 9)))


def billboard_to_topic_cards(data: Any, limit: int = 12) -> List[Dict[str, Any]]:
    """将热榜接口 data 转为前端 TopicCard 所需字段（由 creator 再包一层 topics）"""
    items: List[Any] = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # 首先尝试直接的列表键
        for k in ("list", "data", "items", "records", "aweme_list", "hot_list", "objs"):
            v = data.get(k)
            if isinstance(v, list):
                items = v
                break
        # 如果还没找到，尝试嵌套的 data.data（TikHub 响应格式）
        if not items and "data" in data and isinstance(data["data"], dict):
            nested = data["data"]
            for k in ("list", "data", "items", "records", "aweme_list", "hot_list", "objs"):
                v = nested.get(k)
                if isinstance(v, list):
                    items = v
                    break
        # 再尝试更深一层 data.data.objs（TikHub 高播榜格式）
        if not items and "data" in data and isinstance(data["data"], dict):
            nested = data["data"]
            if "data" in nested and isinstance(nested["data"], dict):
                deep_nested = nested["data"]
                for k in ("list", "data", "items", "records", "aweme_list", "hot_list", "objs"):
                    v = deep_nested.get(k)
                    if isinstance(v, list):
                        items = v
                        break

    out: List[Dict[str, Any]] = []
    seen: set = set()
    for i, item in enumerate(items):
        if len(out) >= limit:
            break
        title = _title_from_item(item, i)
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        
        # 构建抖音搜索链接作为sourceUrl
        aweme_id = _get_nested_str(item, "aweme_id") or ""
        share_url = _get_nested_str(item, "share_url") or ""
        if aweme_id:
            source_url = f"https://www.douyin.com/video/{aweme_id}"
        elif share_url:
            source_url = share_url
        else:
            # 使用标题构建搜索链接（必须 URL 编码，否则 # 等字符会被当作 fragment，导致「点不进去」）
            search_query = title[:80].replace(" ", "").replace("?", "").replace("？", "")
            source_url = f"https://www.douyin.com/search/{quote(search_query, safe='')}"

        play_cnt = _play_count_from_billboard_item(item)
        est_views = _format_views_for_topic_card(play_cnt)
        est_complete = _completion_from_play_count(play_cnt)

        out.append(
            {
                "id": str(len(out) + 1),
                "title": title,
                "originalTitle": title,  # 保留原标题
                "score": _score_from_item(item, len(out)),
                "tags": _tags_from_item(item) or ["抖音", "热榜"],
                "reason": "抖音高播放量热榜（TikHub）",
                "estimatedViews": est_views,
                "estimatedCompletion": est_complete,
                "sourceUrl": source_url,  # 添加原链接
            }
        )
    return out


async def get_recommended_topic_cards(limit: int = 12) -> List[Dict[str, Any]]:
    """供创作端推荐选题：仅返回 TikHub 有效候选（失败时返回空）。"""
    configured = is_configured()
    logger.info(f"[TIKHUB] is_configured: {configured}")
    if not configured:
        logger.warning("[TIKHUB] TIKHUB_API_KEY not configured, returning empty list")
        return []
    try:
        logger.info("[TIKHUB] Fetching high play hot list...")
        # 高播榜使用默认 date_window=2
        raw = await fetch_douyin_high_play_hot_list(page=1, page_size=max(limit, 5))
        logger.info(f"[TIKHUB] High play raw data type: {type(raw)}, has data: {bool(raw)}")
        cards = billboard_to_topic_cards(raw, limit=limit)
        logger.info(f"[TIKHUB] High play cards count: {len(cards)}")
        if cards:
            return cards
        # 高播榜无有效结果时，退到低粉爆款榜作为同源补充池
        logger.info("[TIKHUB] High play empty, trying low fan list...")
        # 低粉榜使用 date_window=1
        raw_low = await fetch_douyin_low_fan_hot_list(page=1, page_size=max(limit, 5), date_window=1)
        logger.info(f"[TIKHUB] Low fan raw data type: {type(raw_low)}, has data: {bool(raw_low)}")
        low_cards = billboard_to_topic_cards(raw_low, limit=limit)
        logger.info(f"[TIKHUB] Low fan cards count: {len(low_cards)}")
        if low_cards:
            return low_cards
    except Exception as e:
        logger.error(f"[TIKHUB] Error fetching from TikHub: {type(e).__name__}: {e}")
        # 尝试获取更详细的错误信息
        if hasattr(e, 'response'):
            try:
                error_body = e.response.json() if hasattr(e.response, 'json') else str(e.response.text)
                logger.error(f"[TIKHUB] Error response: {error_body}")
            except:
                pass
    logger.warning("[TIKHUB] All TikHub sources failed, returning empty list")
    return []
