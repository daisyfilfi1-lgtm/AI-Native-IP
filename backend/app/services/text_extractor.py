"""
统一文本提取服务
整合多种提取策略：TikHub API、Web爬取、yt-dlp
智能选择最优方案
"""
import json
import logging
import os
import re
import shutil
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

import httpx

from app.services import tikhub_client
from app.services.link_resolver import resolve_any_url, detect_platform

logger = logging.getLogger(__name__)


@dataclass
class ExtractResult:
    """提取结果"""
    success: bool
    text: str
    method: str  # tikhub / web_scrape / ytdlp / none
    error: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ============== TikHub 提取 ==============

async def extract_with_tikhub(resolved_url: str, platform: Optional[str] = None) -> ExtractResult:
    """
    使用 TikHub API 提取文本
    """
    if not tikhub_client.is_configured():
        return ExtractResult(
            success=False,
            text="",
            method="tikhub",
            error="TIKHUB_API_KEY 未配置"
        )
    
    try:
        # 抖音链接优先使用 Web 单条接口
        if platform == "douyin" or tikhub_client.looks_like_douyin_share_url(resolved_url):
            try:
                raw = await tikhub_client.fetch_douyin_web_one_video_by_share_url(resolved_url)
                extracted = _extract_from_tikhub_response(raw)
                if extracted:
                    return ExtractResult(
                        success=True,
                        text=extracted,
                        method="tikhub",
                        metadata={"sub_method": "douyin_web_one"}
                    )
            except Exception as e:
                logger.warning(f"TikHub 抖音 Web 接口失败: {e}")
        
        # 通用 hybrid 接口
        raw = await tikhub_client.hybrid_video_data(resolved_url)
        extracted = _extract_from_tikhub_response(raw)
        
        if extracted:
            return ExtractResult(
                success=True,
                text=extracted,
                method="tikhub",
                metadata={"sub_method": "hybrid"}
            )
        
        return ExtractResult(
            success=False,
            text="",
            method="tikhub",
            error="TikHub 返回空内容"
        )
        
    except Exception as e:
        err_msg = str(e)
        # 处理常见错误
        if "403" in err_msg:
            error = "TikHub API 权限不足（403），请检查 API Key 是否有效"
        elif "429" in err_msg or "rate limit" in err_msg.lower():
            error = "TikHub 请求过于频繁（429），请稍后重试"
        elif "404" in err_msg:
            error = "视频不存在或已被删除（404）"
        elif "timeout" in err_msg.lower():
            error = "TikHub 请求超时"
        else:
            error = f"TikHub 提取失败: {err_msg[:100]}"
        
        return ExtractResult(
            success=False,
            text="",
            method="tikhub",
            error=error
        )


def _extract_from_tikhub_response(data: Any) -> str:
    """从 TikHub 响应中提取文本"""
    if not data:
        return ""
    
    if isinstance(data, str):
        return data.strip()[:12000]
    
    if not isinstance(data, dict):
        return str(data)[:12000]
    
    parts = []
    
    # 直接字段
    for key in ["desc", "title", "share_title", "video_title", "text", "content"]:
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    
    # 嵌套结构
    for nested_key in ["aweme_detail", "aweme", "video", "item", "data"]:
        nested = data.get(nested_key)
        if isinstance(nested, dict):
            nested_text = _extract_from_tikhub_response(nested)
            if nested_text:
                parts.append(nested_text)
    
    # 从评论提取（如果有）
    comments = data.get("comments") or []
    if isinstance(comments, list) and len(comments) > 0:
        comment_texts = []
        for c in comments[:3]:  # 取前3条
            if isinstance(c, dict):
                text = c.get("text") or c.get("content", "")
                if text:
                    comment_texts.append(text)
        if comment_texts:
            parts.append("热门评论:\n" + "\n".join(comment_texts))
    
    # 去重拼接
    seen = set()
    unique_parts = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            unique_parts.append(p)
    
    result = "\n\n".join(unique_parts)
    return result[:12000]


# ============== Web 爬取 ==============

MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


async def extract_with_web_scrape(resolved_url: str, platform: Optional[str]) -> ExtractResult:
    """使用 Web 爬取提取文本"""
    if not platform:
        return ExtractResult(
            success=False,
            text="",
            method="web_scrape",
            error="无法识别平台，无法使用 Web 爬取"
        )
    
    extractors = {
        "douyin": _extract_douyin_web,
        "xiaohongshu": _extract_xiaohongshu_web,
        "kuaishou": _extract_kuaishou_web,
        "bilibili": _extract_bilibili_web,
    }
    
    extractor = extractors.get(platform)
    if not extractor:
        return ExtractResult(
            success=False,
            text="",
            method="web_scrape",
            error=f"暂不支持 {platform} 平台的 Web 爬取"
        )
    
    try:
        text = await extractor(resolved_url)
        if text and len(text) > 10:
            return ExtractResult(
                success=True,
                text=text,
                method="web_scrape",
                metadata={"platform": platform}
            )
        return ExtractResult(
            success=False,
            text="",
            method="web_scrape",
            error="Web 爬取返回内容过短或为空"
        )
    except Exception as e:
        return ExtractResult(
            success=False,
            text="",
            method="web_scrape",
            error=f"Web 爬取失败: {e}"
        )


async def _extract_douyin_web(url: str) -> str:
    """爬取抖音移动端页面 - 增强版"""
    # 提取视频ID
    video_id_match = re.search(r"/video/(\d+)", url)
    if not video_id_match:
        return ""
    
    video_id = video_id_match.group(1)
    
    # 方法1: 尝试 embed 页面
    embed_url = f"https://www.douyin.com/embed/{video_id}"
    
    try:
        timeout = httpx.Timeout(15.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(embed_url, headers=MOBILE_HEADERS)
            
            if r.status_code == 200 and len(r.text) > 1000:
                html = r.text
                
                # 尝试从 embed 页面提取
                # 查找 JSON 数据
                patterns = [
                    r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                    r'window\.__UNIVERSAL_DATA__\s*=\s*({.+?});',
                    r'"desc"\s*:\s*"([^"]*)"',
                    r'<title>([^<]+)</title>',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, html)
                    if match:
                        if "INITIAL_STATE" in pattern or "UNIVERSAL_DATA" in pattern:
                            try:
                                import json
                                data = json.loads(match.group(1))
                                # 递归找 desc
                                desc = _find_value_recursive(data, ['desc', 'title', 'share_title'])
                                if desc:
                                    return desc[:2000]
                            except:
                                pass
                        else:
                            text = match.group(1).strip()
                            if text and len(text) > 5 and "抖音" not in text:
                                return text[:2000]
    except Exception as e:
        logger.debug(f"抖音 embed 失败: {e}")
    
    # 方法2: PC 页面 + 从 script 提取
    try:
        timeout = httpx.Timeout(15.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            if r.status_code == 200:
                html = r.text
                
                # 尝试从 script 中提取 JSON
                # 抖音 PC 页面有 __NEXT_DATA__ 或 __UNIVERSAL_DATA__
                patterns = [
                    r'window\.__UNIVERSAL_DATA__\s*=\s*({.+?});',
                    r'window\.__NEXT_DATA__\s*=\s*({.+?});',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, html)
                    if match:
                        try:
                            import json
                            data = json.loads(match.group(1))
                            desc = _find_value_recursive(data, ['desc', 'title', 'share_title', 'video_title'])
                            if desc:
                                return desc[:2000]
                        except:
                            pass
                
                # 从 meta 标签提取
                for meta_pattern in [
                    r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
                    r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
                ]:
                    match = re.search(meta_pattern, html, re.I)
                    if match:
                        text = match.group(1).strip()
                        if text and len(text) > 10:
                            return text[:2000]
                
                # 从 title 提取
                title_match = re.search(r'<title>([^<]+)</title>', html)
                if title_match:
                    title = title_match.group(1).strip()
                    if title and "抖音" not in title:
                        return title[:2000]
    except Exception as e:
        logger.warning(f"抖音 PC 页面爬取失败: {e}")
    
    return ""


def _find_value_recursive(obj, keys, depth=0):
    """递归查找包含指定 key 的值"""
    if depth > 5:
        return None
    
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, str) and v.strip():
                return v.strip()
            if isinstance(v, (dict, list)):
                result = _find_value_recursive(v, keys, depth + 1)
                if result:
                    return result
    elif isinstance(obj, list) and obj:
        return _find_value_recursive(obj[0], keys, depth + 1)
    
    return None


async def _extract_xiaohongshu_web(url: str) -> str:
    """爬取小红书页面"""
    try:
        timeout = httpx.Timeout(20.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(
                url,
                headers={
                    **MOBILE_HEADERS,
                    "Referer": "https://www.xiaohongshu.com/",
                }
            )
            
            if r.status_code != 200:
                return ""
            
            html = r.text
            parts = []
            
            # 提取标题
            title_patterns = [
                r'<meta[^>]*name=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
                r'<title>([^<]+)</title>',
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    if title and "小红书" not in title:
                        parts.append(title)
                        break
            
            # 从 JSON 数据提取内容
            # 小红书页面包含 SSR 数据
            json_pattern = r'<script[^>]*>window\.__INITIAL_STATE__\s*=\s*({.+?})</script>'
            match = re.search(json_pattern, html)
            if match:
                try:
                    data = json.loads(match.group(1))
                    # 遍历数据结构找内容
                    def find_content(obj, depth=0):
                        if depth > 5:
                            return None
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if k in ["desc", "content", "text", "note", "title"]:
                                    if isinstance(v, str) and len(v) > 10:
                                        return v
                                if isinstance(v, (dict, list)):
                                    result = find_content(v, depth + 1)
                                    if result:
                                        return result
                        elif isinstance(obj, list):
                            for item in obj:
                                result = find_content(item, depth + 1)
                                if result:
                                    return result
                        return None
                    
                    content = find_content(data)
                    if content:
                        parts.append(content)
                except:
                    pass
            
            # 去重拼接
            seen = set()
            unique_parts = []
            for p in parts:
                if p and p not in seen:
                    seen.add(p)
                    unique_parts.append(p)
            
            return "\n\n".join(unique_parts)[:3000]
            
    except Exception as e:
        logger.warning(f"小红书爬取失败: {e}")
        return ""


async def _extract_kuaishou_web(url: str) -> str:
    """爬取快手页面"""
    try:
        timeout = httpx.Timeout(15.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(url, headers=MOBILE_HEADERS)
            
            if r.status_code != 200:
                return ""
            
            html = r.text
            
            # 提取标题和描述
            patterns = [
                r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
                r'<title>([^<]+)</title>',
            ]
            
            parts = []
            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    text = match.group(1).strip()
                    if text:
                        parts.append(text)
            
            return "\n".join(parts)[:2000]
            
    except Exception as e:
        logger.warning(f"快手爬取失败: {e}")
        return ""


async def _extract_bilibili_web(url: str) -> str:
    """爬取B站页面"""
    try:
        timeout = httpx.Timeout(15.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.bilibili.com",
                }
            )
            
            if r.status_code != 200:
                return ""
            
            html = r.text
            
            # B站页面数据
            patterns = [
                r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
                r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
                r'<h1[^>]*title=["\']([^"\']+)["\']',
            ]
            
            parts = []
            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    text = match.group(1).strip()
                    if text:
                        parts.append(text)
            
            return "\n".join(parts)[:2000]
            
    except Exception as e:
        logger.warning(f"B站爬取失败: {e}")
        return ""


# ============== yt-dlp ==============

async def extract_with_ytdlp(resolved_url: str) -> ExtractResult:
    """使用 yt-dlp 提取元数据"""
    if not _ytdlp_enabled():
        return ExtractResult(
            success=False,
            text="",
            method="ytdlp",
            error="yt-dlp 未启用（设置 REMIX_YTDLP_FALLBACK=1 启用）"
        )
    
    exe = shutil.which("yt-dlp") or shutil.which("yt_dlp")
    if not exe:
        return ExtractResult(
            success=False,
            text="",
            method="ytdlp",
            error="yt-dlp 未安装"
        )
    
    try:
        import asyncio
        proc = await asyncio.create_subprocess_exec(
            exe,
            "--skip-download",
            "--no-warnings",
            "--dump-single-json",
            resolved_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=45.0)
        
        if proc.returncode != 0:
            err_msg = (err_b or b"").decode("utf-8", errors="replace")[:200]
            return ExtractResult(
                success=False,
                text="",
                method="ytdlp",
                error=f"yt-dlp 失败: {err_msg}"
            )
        
        data = json.loads(out_b.decode("utf-8", errors="replace"))
        
        # 提取元数据
        parts = []
        for key in ["title", "description", "uploader", "channel"]:
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())
        
        text = "\n\n".join(parts)
        
        if text:
            return ExtractResult(
                success=True,
                text=text[:8000],
                method="ytdlp",
                metadata={"extractor": data.get("extractor", "unknown")}
            )
        
        return ExtractResult(
            success=False,
            text="",
            method="ytdlp",
            error="yt-dlp 返回空内容"
        )
        
    except asyncio.TimeoutError:
        return ExtractResult(
            success=False,
            text="",
            method="ytdlp",
            error="yt-dlp 超时"
        )
    except Exception as e:
        return ExtractResult(
            success=False,
            text="",
            method="ytdlp",
            error=f"yt-dlp 异常: {e}"
        )


def _ytdlp_enabled() -> bool:
    v = os.environ.get("REMIX_YTDLP_FALLBACK", "").strip().lower()
    return v in ("1", "true", "yes", "on")


# ============== 统一入口 ==============

async def extract_text(url: str, prefer_method: Optional[str] = None) -> ExtractResult:
    """
    统一的文本提取入口
    
    参数:
        url: 视频链接
        prefer_method: 优先使用的提取方法 (tikhub / web_scrape / ytdlp)
    
    返回:
        ExtractResult 对象
    """
    logger.info(f"开始提取文本: {url[:60]}...")
    
    # 步骤1: 解析链接
    resolve_result = await resolve_any_url(url)
    
    if resolve_result["error"] and not resolve_result["resolved_url"]:
        return ExtractResult(
            success=False,
            text="",
            method="none",
            error=f"链接解析失败: {resolve_result['error']}"
        )
    
    resolved_url = resolve_result["resolved_url"]
    platform = resolve_result["platform"]
    
    logger.info(f"链接解析完成: platform={platform}, resolved={resolved_url[:60]}...")
    
    # 定义提取策略顺序
    strategies = []
    
    if prefer_method == "tikhub":
        strategies = [
            ("tikhub", lambda: extract_with_tikhub(resolved_url, platform)),
            ("web_scrape", lambda: extract_with_web_scrape(resolved_url, platform)),
            ("ytdlp", lambda: extract_with_ytdlp(resolved_url)),
        ]
    elif prefer_method == "web_scrape":
        strategies = [
            ("web_scrape", lambda: extract_with_web_scrape(resolved_url, platform)),
            ("tikhub", lambda: extract_with_tikhub(resolved_url, platform)),
            ("ytdlp", lambda: extract_with_ytdlp(resolved_url)),
        ]
    else:
        # 默认顺序: TikHub -> Web -> yt-dlp
        strategies = [
            ("tikhub", lambda: extract_with_tikhub(resolved_url, platform)),
            ("web_scrape", lambda: extract_with_web_scrape(resolved_url, platform)),
            ("ytdlp", lambda: extract_with_ytdlp(resolved_url)),
        ]
    
    # 尝试每种策略
    errors = []
    for method_name, extractor_func in strategies:
        try:
            result = await extractor_func()
            if result.success and len(result.text) > 10:
                logger.info(f"提取成功: method={result.method}, length={len(result.text)}")
                # 添加解析元数据
                result.metadata.update({
                    "original_url": url,
                    "resolved_url": resolved_url,
                    "platform": platform,
                    "resolve_error": resolve_result.get("error"),
                })
                return result
            else:
                errors.append(f"{result.method}: {result.error}")
        except Exception as e:
            errors.append(f"{method_name}: {e}")
    
    # 所有策略都失败
    error_msg = "所有提取方法都失败:\n" + "\n".join(errors)
    logger.error(error_msg)
    
    return ExtractResult(
        success=False,
        text="",
        method="none",
        error=error_msg,
        metadata={
            "original_url": url,
            "resolved_url": resolved_url,
            "platform": platform,
        }
    )
