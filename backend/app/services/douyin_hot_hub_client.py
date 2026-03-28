"""
douyin-hot-hub 数据客户端：
- 数据源: https://github.com/SnailDev/douyin-hot-hub
- 读取 README 最新热榜，并做本地 24h 缓存，避免频繁请求。
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

README_URL = "https://raw.githubusercontent.com/SnailDev/douyin-hot-hub/main/README.md"
_HOT_LINE_RE = re.compile(r"^\s*\d+\.\s+\[(.*?)\]\((https?://[^\s)]+)\)\s*$")
_BUNDLED_SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "douyin_hot_hub_snapshot.json"


def _default_cache_path() -> Path:
    override = (os.environ.get("DOUYIN_HOT_HUB_CACHE_FILE") or "").strip()
    if override:
        return Path(override)
    # Railway 容器建议用 /tmp；本地开发用仓库内 .cache
    if (os.environ.get("RAILWAY_ENVIRONMENT_NAME") or "").strip():
        return Path("/tmp/douyin_hot_hub_cache.json")
    return Path(__file__).resolve().parents[2] / ".cache" / "douyin_hot_hub_cache.json"


def _load_cache(path: Path, max_age_hours: int) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = str(obj.get("fetched_at") or "").strip()
        cards = obj.get("cards")
        if not fetched_at or not isinstance(cards, list):
            return []
        ts = datetime.fromisoformat(fetched_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - ts > timedelta(hours=max_age_hours):
            return []
        return [c for c in cards if isinstance(c, dict)]
    except Exception as e:
        logger.warning("douyin-hot-hub cache read failed: %s", e)
        return []


def _save_cache(path: Path, cards: List[Dict[str, Any]]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "cards": cards,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning("douyin-hot-hub cache write failed: %s", e)


def _load_bundled_snapshot(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        cards = obj.get("cards")
        if not isinstance(cards, list):
            return []
        out = [c for c in cards if isinstance(c, dict)]
        if out:
            logger.info("douyin-hot-hub using bundled snapshot, count=%s", len(out))
        return out
    except Exception as e:
        logger.warning("douyin-hot-hub bundled snapshot read failed: %s", e)
        return []


def _parse_hot_cards(markdown: str, limit: int) -> List[Dict[str, Any]]:
    lines = markdown.splitlines()
    in_hot = False
    cards: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            in_hot = s == "## 抖音热榜"
            continue
        if not in_hot:
            continue
        if not s:
            continue
        m = _HOT_LINE_RE.match(s)
        if not m:
            continue
        title = m.group(1).strip()
        url = m.group(2).strip()
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        rank = len(cards) + 1
        # 归一化一个热度分（用于后续四维重排）；越靠前分越高。
        score = round(max(4.0, 4.95 - (rank - 1) * 0.03), 2)
        cards.append(
            {
                "id": f"dyhub_{rank}",
                "title": title[:200],
                "score": score,
                "tags": ["抖音", "热榜"],
                "reason": "抖音热榜（douyin-hot-hub）",
                "estimatedViews": "—",
                "estimatedCompletion": 35,
                "sourceUrl": url,
            }
        )
        if len(cards) >= limit:
            break
    return cards


async def get_recommended_topic_cards(limit: int = 12, max_age_hours: int = 24) -> List[Dict[str, Any]]:
    path = _default_cache_path()
    cached = _load_cache(path, max_age_hours=max_age_hours)
    if cached:
        return cached[:limit]

    try:
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(README_URL)
            r.raise_for_status()
            markdown = r.text
        cards = _parse_hot_cards(markdown, limit=max(20, limit))
        if cards:
            _save_cache(path, cards)
            return cards[:limit]
    except Exception as e:
        logger.warning("douyin-hot-hub fetch failed: %s", e)

    bundled = _load_bundled_snapshot(_BUNDLED_SNAPSHOT_PATH)
    if bundled:
        return bundled[:limit]
    return []

