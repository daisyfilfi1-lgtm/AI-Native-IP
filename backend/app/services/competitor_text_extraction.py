"""
链接 → 仿写信源文本：可插拔链路（TikHub → yt-dlp → Web爬取 → URL 兜底）。

- TikHub：见 tikhub_client.try_extract_competitor_text_tikhub
- yt-dlp：需镜像内安装 `yt-dlp` 可执行文件，并设置 REMIX_YTDLP_FALLBACK=1
- Web爬取：直接请求抖音/小红书移动端页面，提取标题和简介
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from typing import Any, Dict, List, Optional

import httpx

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


# ==================== Web 爬取方案 ====================

MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


async def _extract_douyin_web(url: str) -> str:
    """直接爬取抖音移动端页面提取文案"""
    try:
        # 抖音移动端页面
        mobile_url = url
        if "www.douyin.com" in url:
            # 尝试获取 embed 页面
            video_id = re.search(r'/video/(\d+)', url)
            if video_id:
                mobile_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id.group(1)}"
        
        timeout = httpx.Timeout(15.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # 尝试 API 接口
            if "/aweme/v1/web/aweme/detail/" in mobile_url:
                r = await client.get(mobile_url, headers=MOBILE_HEADERS)
                if r.status_code == 200:
                    data = r.json()
                    aweme_detail = data.get("aweme_detail", {})
                    desc = aweme_detail.get("desc", "")
                    if desc:
                        return desc.strip()
            
            # 回退到网页爬取
            r = await client.get(url, headers=MOBILE_HEADERS)
            if r.status_code == 200:
                html = r.text
                # 尝试从 JSON 提取
                patterns = [
                    r'"desc"\s*:\s*"([^"]*)"',
                    r'"description"\s*:\s*"([^"]*)"',
                    r'"share_title"\s*:\s*"([^"]*)"',
                ]
                for pat in patterns:
                    match = re.search(pat, html)
                    if match:
                        text = match.group(1).strip()
                        if text:
                            return text[:2000]
                # 从 <title> 提取
                title_match = re.search(r'<title>([^<]+)</title>', html)
                if title_match:
                    return title_match.group(1).strip()
    except Exception as e:
        logger.warning(f"抖音Web爬取失败: {e}")
    return ""


async def _extract_xiaohongshu_web(url: str) -> str:
    """直接爬取小红书移动端页面提取文案"""
    try:
        timeout = httpx.Timeout(15.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # 小红书移动端
            r = await client.get(url, headers=MOBILE_HEADERS)
            if r.status_code == 200:
                html = r.text
                # 从 JSON 提取标题和内容
                patterns = [
                    r'"title"\s*:\s*"([^"]*)"',
                    r'"desc"\s*:\s*"([^"]*)"',
                    r'"noteTitle"\s*:\s*"([^"]*)"',
                    r'"content"\s*:\s*"([^"]*)"',
                ]
                parts = []
                for pat in patterns:
                    matches = re.findall(pat, html)
                    for m in matches[:2]:  # 取前2个
                        if m and len(m) > 5:
                            parts.append(m.strip())
                if parts:
                    return "\n\n".join(parts)[:2000]
    except Exception as e:
        logger.warning(f"小红书Web爬取失败: {e}")
    return ""


async def _try_web_scraper(url: str) -> str:
    """Web 爬取入口 - 自动识别平台"""
    low = url.lower()
    
    if "douyin.com" in low:
        return await _extract_douyin_web(url)
    elif "xiaohongshu.com" in low or "xhslink" in low:
        return await _extract_xiaohongshu_web(url)
    
    return ""


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

    # 3. Web 爬取备选（不依赖 TikHub）
    logger.info("尝试 Web 爬取...")
    web_text = await _try_web_scraper(resolved)
    if web_text.strip():
        logger.info(f"Web 爬取成功，长度: {len(web_text)}")
        return web_text.strip()

    # 4. yt-dlp 备选
    if _ytdlp_enabled():
        logger.info("尝试 yt-dlp 备选...")
        ytdlp_text = await _try_ytdlp_metadata_text(resolved)
        if ytdlp_text.strip():
            logger.info(f"yt-dlp 提取成功，长度: {len(ytdlp_text)}")
            return ytdlp_text.strip()

    # 5. 兜底：从 URL 尝试提取有用信息
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


async def extract_competitor_text_with_fallback(url: str) -> dict:
    """
    带诊断信息的竞品文本提取。
    
    返回:
        dict: {
            "success": bool,
            "text": str,  # 成功时为提取的文本，失败时为""
            "error": str,  # 失败时的错误信息
            "method": str,  # 使用的提取方法
        }
    """
    u = (url or "").strip()
    if not u:
        return {
            "success": False,
            "text": "",
            "error": "链接不能为空",
            "method": "none"
        }

    # 1. 短链解析
    try:
        resolved = await resolve_short_url(u)
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "error": f"短链解析失败: {e}",
            "method": "none"
        }

    # 2. TikHub 提取
    if tikhub_client.is_configured():
        try:
            t = await tikhub_client.try_extract_competitor_text_tikhub(resolved)
            if t and t.strip():
                return {
                    "success": True,
                    "text": t.strip(),
                    "error": "",
                    "method": "tikhub"
                }
        except Exception as e:
            logger.warning(f"TikHub提取失败: {e}")

    # 3. yt-dlp 备选
    if _ytdlp_enabled():
        try:
            ytdlp_text = await _try_ytdlp_metadata_text(resolved)
            if ytdlp_text.strip():
                return {
                    "success": True,
                    "text": ytdlp_text.strip(),
                    "error": "",
                    "method": "ytdlp"
                }
        except Exception as e:
            logger.warning(f"yt-dlp提取失败: {e}")

    # 4. 都失败
    return {
        "success": False,
        "text": "",
        "error": "无法从链接提取内容。可能原因：\n1. TIKHUB_API_KEY未配置\n2. 链接无效或视频已删除\n3. 网络连接问题",
        "method": "none"
    }
