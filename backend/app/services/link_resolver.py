"""
链接解析器 - 处理各种短视频平台的链接解析
支持：抖音、小红书、视频号、快手、B站
"""
import re
import logging
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs, unquote

import httpx

logger = logging.getLogger(__name__)

# 平台识别模式
PLATFORM_PATTERNS = {
    "douyin": [
        r"v\.douyin\.com",
        r"www\.douyin\.com/video/",
        r"www\.iesdouyin\.com",
    ],
    "xiaohongshu": [
        r"xhslink\.com",
        r"www\.xiaohongshu\.com",
    ],
    "kuaishou": [
        r"v\.kuaishou\.com",
        r"www\.kuaishou\.com/short-video/",
    ],
    "bilibili": [
        r"b23\.tv",
        r"www\.bilibili\.com/video/",
    ],
    "weixin_video": [
        r"weixin\.qq\.com",
        r"channels-share\.weixin\.qq\.com",
    ],
}

MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

PC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def detect_platform(url: str) -> Optional[str]:
    """识别链接所属平台"""
    url_lower = url.lower()
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url_lower):
                return platform
    return None


def extract_video_id(url: str, platform: str) -> Optional[str]:
    """从 URL 中提取视频 ID"""
    if platform == "douyin":
        # 抖音视频ID
        match = re.search(r"/video/(\d+)", url)
        if match:
            return match.group(1)
        # 短链中的ID
        match = re.search(r"video/(\d+)", url)
        if match:
            return match.group(1)
    elif platform == "kuaishou":
        # 快手视频ID
        match = re.search(r"short-video/(\w+)", url)
        if match:
            return match.group(1)
    elif platform == "bilibili":
        # B站 BV号
        match = re.search(r"video/(BV\w+)", url)
        if match:
            return match.group(1)
        # B站 av号
        match = re.search(r"video/(av\d+)", url)
        if match:
            return match.group(1)
    elif platform == "xiaohongshu":
        # 小红书笔记ID
        match = re.search(r"/explore/(\w+)", url)
        if match:
            return match.group(1)
        match = re.search(r"note/(\w+)", url)
        if match:
            return match.group(1)
    return None


async def resolve_douyin_short(url: str) -> Tuple[str, Optional[str]]:
    """
    解析抖音短链
    返回: (解析后的URL, 错误信息)
    """
    try:
        timeout = httpx.Timeout(15.0, connect=8.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # 先尝试移动端 UA
            r = await client.get(url, headers=MOBILE_HEADERS)
            final_url = str(r.url).split("#")[0]
            
            # 检查是否被拦截
            if "verify" in final_url.lower() or "captcha" in final_url.lower():
                logger.warning("抖音短链触发验证")
                # 尝试 PC 端
                r = await client.get(url, headers=PC_HEADERS)
                final_url = str(r.url).split("#")[0]
            
            # 检查是否解析为用户主页
            if "/user/" in final_url or "/share/user" in final_url:
                return url, "该链接是用户主页，不是视频链接"
            
            # 检查是否有效视频链接
            if "/video/" not in final_url:
                return url, f"无法解析为视频链接: {final_url[:100]}"
            
            return final_url, None
            
    except httpx.TimeoutException:
        return url, "解析超时，请检查网络连接"
    except Exception as e:
        logger.warning(f"抖音短链解析失败: {e}")
        return url, f"解析失败: {e}"


async def resolve_xiaohongshu_short(url: str) -> Tuple[str, Optional[str]]:
    """
    解析小红书短链
    返回: (解析后的URL, 错误信息)
    """
    # 小红书短链通常需要 https
    if url.startswith("http://"):
        url = "https://" + url[7:]
    
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
            final_url = str(r.url).split("#")[0]
            
            # 检查是否404
            if r.status_code == 404 or "/404" in final_url:
                return url, "该笔记已删除或链接已过期"
            
            # 检查是否需要登录
            if "login" in final_url.lower():
                return url, "该笔记需要登录才能查看"
            
            return final_url, None
            
    except httpx.TimeoutException:
        return url, "解析超时，请检查网络连接"
    except Exception as e:
        logger.warning(f"小红书短链解析失败: {e}")
        return url, f"解析失败: {e}"


async def resolve_kuaishou_short(url: str) -> Tuple[str, Optional[str]]:
    """解析快手短链"""
    try:
        timeout = httpx.Timeout(15.0, connect=8.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(url, headers=MOBILE_HEADERS)
            final_url = str(r.url).split("#")[0]
            
            if "404" in final_url or r.status_code == 404:
                return url, "该视频已删除或不存在"
            
            return final_url, None
            
    except Exception as e:
        logger.warning(f"快手短链解析失败: {e}")
        return url, None  # 静默失败，使用原链接


async def resolve_bilibili_short(url: str) -> Tuple[str, Optional[str]]:
    """解析B站短链"""
    try:
        timeout = httpx.Timeout(15.0, connect=8.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(url, headers=PC_HEADERS)
            final_url = str(r.url).split("#")[0]
            return final_url, None
            
    except Exception as e:
        logger.warning(f"B站短链解析失败: {e}")
        return url, None


async def resolve_any_url(url: str) -> dict:
    """
    通用链接解析入口
    
    返回:
        {
            "original_url": str,
            "resolved_url": str,
            "platform": str | None,
            "video_id": str | None,
            "error": str | None,
            "is_short_link": bool,
        }
    """
    original = url.strip()
    if not original:
        return {
            "original_url": "",
            "resolved_url": "",
            "platform": None,
            "video_id": None,
            "error": "链接不能为空",
            "is_short_link": False,
        }
    
    # 识别平台
    platform = detect_platform(original)
    
    # 判断是否为短链
    is_short = any(x in original.lower() for x in [
        "v.douyin.com", "xhslink.com", "v.kuaishou.com", 
        "b23.tv", "t.cn"
    ])
    
    # 解析短链
    resolved = original
    error = None
    
    if is_short:
        logger.info(f"检测到短链，开始解析: {platform}")
        
        if platform == "douyin":
            resolved, error = await resolve_douyin_short(original)
        elif platform == "xiaohongshu":
            resolved, error = await resolve_xiaohongshu_short(original)
        elif platform == "kuaishou":
            resolved, error = await resolve_kuaishou_short(original)
        elif platform == "bilibili":
            resolved, error = await resolve_bilibili_short(original)
    
    # 提取视频ID
    video_id = extract_video_id(resolved, platform) if platform else None
    
    # 如果解析出错，但resolved还是原链接，尝试继续
    if error and resolved == original:
        logger.warning(f"短链解析失败但继续使用原链接: {error}")
        error = None  # 不阻断流程
    
    return {
        "original_url": original,
        "resolved_url": resolved,
        "platform": platform,
        "video_id": video_id,
        "error": error,
        "is_short_link": is_short,
    }
