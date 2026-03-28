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
    仿写入口：解析短链后依次尝试 TikHub、（可选）yt-dlp，最后退回标题+URL。
    增强：支持抖音短链解析、多层 fallback、日志诊断
    """
    u = (url or "").strip()
    if not u:
        logger.warning("extract_competitor_text_for_remix: 空URL")
        return ""

    # 1. 短链解析（抖音 v.douyin.com + 小红书 xhslink.com）
    resolved = await resolve_short_url(u)
    logger.info(f"短链解析: {u[:50]}... → {resolved[:50]}...")
    
    # 检测短链是否解析失败
    if "xiaohongshu.com/404" in resolved.lower():
        logger.error("小红书短链已过期或无效")
        return "【链接已失效】该小红书链接已过期，请获取最新的分享链接"
    
    if "iesdouyin.com/share/user" in resolved:
        logger.error("抖音短链解析为用户主页，无法获取视频内容")
        return "【链接类型错误】该链接是用户主页，请复制具体视频的分享链接（包含 /video/ 的链接）"

    # 2. TikHub 提取（主方案）
    if tikhub_client.is_configured():
        logger.info("尝试 TikHub 提取...")
        try:
            t = await tikhub_client.try_extract_competitor_text_tikhub(resolved)
            if t and t.strip():
                logger.info(f"TikHub 提取成功，长度: {len(t)}")
                return t.strip()
            else:
                logger.warning("TikHub 返回空")
        except Exception as e:
            err_msg = str(e)
            if "403" in err_msg and "permissions" in err_msg.lower():
                logger.error("TikHub API 权限不足：请前往 https://user.tikhub.io/dashboard/api 开启 hybrid/video_data 权限")
                return "【API权限不足】请在 TikHub 后台开启 API 权限：https://user.tikhub.io/dashboard/api"
            logger.error(f"TikHub 提取异常: {type(e).__name__}: {e}")

    # 3. yt-dlp 备选
    if _ytdlp_enabled():
        logger.info("尝试 yt-dlp 备选...")
        ytdlp_text = await _try_ytdlp_metadata_text(resolved)
        if ytdlp_text.strip():
            logger.info(f"yt-dlp 提取成功，长度: {len(ytdlp_text)}")
            return ytdlp_text.strip()

    # 4. 兜底：从 URL 尝试提取有用信息
    fallback = build_fallback_text(resolved)
    logger.warning(f"所有方案失败，使用兜底方案: {len(fallback)} 字符")
    return fallback


async def resolve_short_url(url: str) -> str:
    """解析抖音/小红书短链为真实 URL"""
    u = (url or "").strip()
    if not u:
        return u
    
    low = u.lower()
    
    # 小红书短链
    if "xhslink.com" in low:
        return await tikhub_client.resolve_share_url_for_tikhub(u)
    
    # 抖音短链 v.douyin.com/xxx
    if "v.douyin.com" in low or "douyin.com" in low and "/jump" in u:
        try:
            import httpx
            timeout = httpx.Timeout(15.0, connect=8.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                r = await client.get(
                    u,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                final = str(r.url)
                if final.startswith("http"):
                    return final.split("#")[0]
        except Exception as e:
            logger.warning(f"抖音短链解析失败: {e}")
    
    return u


def build_fallback_text(url: str) -> str:
    """兜底方案：从 URL 提取主题信息"""
    if not url:
        return ""
    
    # 尝试从 URL 提取有用信息
    parts = []
    
    # 提取路径中的关键词
    from urllib.parse import urlparse, parse_qs
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        # 抖音视频 ID
        if "/video/" in path:
            vid = path.split("/video/")[-1].split("/")[0].split("?")[0]
            parts.append(f"抖音视频ID: {vid}")
        
        # 小红书笔记 ID  
        if "/explore/" in path:
            nid = path.split("/explore/")[-1].split("/")[0].split("?")[0]
            parts.append(f"小红书笔记ID: {nid}")
        
        # 从域名提取平台
        domain = parsed.netloc.lower()
        if "douyin" in domain:
            parts.append("来源: 抖音")
        elif "xiaohongshu" in domain or "xhslink" in domain:
            parts.append("来源: 小红书")
            
    except Exception as e:
        logger.debug(f"URL解析失败: {e}")
    
    if parts:
        return "".join(parts) + f"\n原始链接: {url[:2000]}"
    
    return url[:2000]
