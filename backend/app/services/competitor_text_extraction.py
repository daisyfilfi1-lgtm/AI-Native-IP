"""
链接 → 仿写信源文本：可插拔链路（TikHub → 可选 yt-dlp → URL 兜底）。

- TikHub：见 tikhub_client.try_extract_competitor_text_tikhub
- yt-dlp：需镜像内安装 `yt-dlp` 可执行文件，并设置 REMIX_YTDLP_FALLBACK=1
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from typing import Any, Dict, List, Optional

from app.services import tikhub_client

logger = logging.getLogger(__name__)


def _ytdlp_enabled() -> bool:
    v = os.environ.get("REMIX_YTDLP_FALLBACK", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _lines_from_ytdlp_json(data: Dict[str, Any]) -> List[str]:
    parts: List[str] = []
    for key in ("title", "description", "uploader", "channel", "alt_title"):
        v = data.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    # 部分站点把简介放在子字段
    for sub in ("track", "artist"):
        v = data.get(sub)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    webpage = data.get("webpage_url")
    if isinstance(webpage, str) and webpage.strip():
        parts.append(webpage.strip())
    # 去重保序
    return list(dict.fromkeys(p for p in parts if p))


async def _try_ytdlp_metadata_text(url: str) -> str:
    if not _ytdlp_enabled():
        return ""
    exe = shutil.which("yt-dlp") or shutil.which("yt_dlp")
    if not exe:
        return ""
    try:
        proc = await asyncio.create_subprocess_exec(
            exe,
            "--skip-download",
            "--no-warnings",
            "--dump-single-json",
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=45.0)
    except asyncio.TimeoutError:
        logger.warning("yt-dlp 超时 url=%s", url[:120])
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        return ""
    except Exception as e:
        logger.warning("yt-dlp 调用失败: %s", e)
        return ""

    if proc.returncode != 0:
        msg = (err_b or b"").decode("utf-8", errors="replace")[:400]
        logger.debug("yt-dlp exit=%s stderr=%s", proc.returncode, msg)
        return ""

    try:
        raw = (out_b or b"").decode("utf-8", errors="replace")
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ""

    if not isinstance(data, dict):
        return ""

    lines = _lines_from_ytdlp_json(data)
    text = "\n\n".join(lines)
    return text[:12000] if text.strip() else ""


async def extract_competitor_text_for_remix(url: str) -> str:
    """
    仿写入口：解析短链后依次尝试 TikHub、（可选）yt-dlp，最后退回截断 URL。
    """
    u = (url or "").strip()
    if not u:
        return ""

    resolved = await tikhub_client.resolve_share_url_for_tikhub(u)

    if tikhub_client.is_configured():
        t = await tikhub_client.try_extract_competitor_text_tikhub(resolved)
        if t and t.strip():
            return t.strip()

    ytdlp_text = await _try_ytdlp_metadata_text(resolved)
    if ytdlp_text.strip():
        logger.info("仿写信源：yt-dlp 元数据（REMIX_YTDLP_FALLBACK）")
        return ytdlp_text.strip()

    return resolved[:8000]
