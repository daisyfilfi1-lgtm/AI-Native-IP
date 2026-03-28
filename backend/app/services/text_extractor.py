"""
统一文本提取服务
整合多种提取策略：Web 爬取、yt-dlp、Playwright、可选 TikHub API。

抖音/小红书：默认优先自研链路（Web → yt-dlp → Playwright），TikHub 置后且可用
REMIX_SKIP_TIKHUB=1 跳过。Web 结果过短（REMIX_MIN_WEB_CHARS，默认 50）视为失败并继续尝试。
Playwright 使用 domcontentloaded + 页面内 JSON（__UNIVERSAL_DATA__ 等）解析，避免 networkidle 卡死。
"""
import json
import logging
import os
import re
import shutil
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

import httpx

from app.services import tikhub_client
from app.services.link_resolver import resolve_any_url, detect_platform

logger = logging.getLogger(__name__)

# 抖音/小红书：纯 HTTP 常只拿到标题或壳页面，过短则视为失败，继续走 yt-dlp / Playwright
_DEFAULT_MIN_WEB_CHARS = 50


def _min_web_chars_for_platform(platform: Optional[str]) -> int:
    raw = os.environ.get("REMIX_MIN_WEB_CHARS", "").strip()
    if raw.isdigit():
        return max(10, int(raw))
    return _DEFAULT_MIN_WEB_CHARS


def _tikhub_in_chain() -> bool:
    return os.environ.get("REMIX_SKIP_TIKHUB", "").strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    )


def _is_weak_web_extract(text: str, platform: Optional[str]) -> bool:
    if platform not in ("douyin", "xiaohongshu"):
        return False
    if not text or not text.strip():
        return True
    return len(text.strip()) < _min_web_chars_for_platform(platform)


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

# 增强版浏览器 Headers - 模拟真实浏览器
MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

DESKTOP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

# 平台特定的 Headers
PLATFORM_HEADERS = {
    "douyin": {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Referer": "https://www.douyin.com/",
    },
    "xiaohongshu": {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Referer": "https://www.xiaohongshu.com/",
    },
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
    """爬取小红书页面 - 增强版"""
    try:
        timeout = httpx.Timeout(20.0, connect=10.0)
        
        # 方法1: 移动端页面
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(
                url,
                headers={
                    **MOBILE_HEADERS,
                    "Referer": "https://www.xiaohongshu.com/",
                }
            )
            
            if r.status_code == 302 or "/404" in str(r.url):
                logger.warning(f"小红书链接已失效或需要登录: {url}")
                return ""
            
            html = r.text
            parts = []
            
            # 1. 从 meta 标签提取标题
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
            
            # 2. 从 JSON 数据提取内容 (SSR)
            json_patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'window\.__UNIVERSAL_DATA__\s*=\s*({.+?});',
            ]
            
            for jp in json_patterns:
                match = re.search(jp, html)
                if match:
                    try:
                        import json
                        data = json.loads(match.group(1))
                        
                        # 递归找内容字段
                        def find_content(obj, depth=0):
                            if depth > 4:
                                return None
                            if isinstance(obj, dict):
                                for k in ["desc", "content", "text", "note", "title", "share_title"]:
                                    if k in obj and isinstance(obj[k], str) and len(obj[k]) > 10:
                                        return obj[k]
                                for v in obj.values():
                                    if isinstance(v, (dict, list)):
                                        result = find_content(v, depth + 1)
                                        if result:
                                            return result
                            elif isinstance(obj, list) and obj:
                                return find_content(obj[0], depth + 1)
                            return None
                        
                        content = find_content(data)
                        if content:
                            parts.append(content)
                    except Exception as e:
                        logger.debug(f"小红书JSON解析失败: {e}")
            
            # 3. 如果上述都失败，尝试从 HTML 结构提取
            if not parts or len("".join(parts)) < 20:
                # 尝试从 script 标签提取
                script_pattern = r'<script[^>]*id="[^"]*initial[^"]*"[^>]*>(.+?)</script>'
                match = re.search(script_pattern, html)
                if match:
                    try:
                        import json
                        data = json.loads(match.group(1))
                        desc = find_content(data)
                        if desc:
                            parts.append(desc)
                    except:
                        pass
            
            # 去重
            seen = set()
            unique_parts = []
            for p in parts:
                if p and p not in seen:
                    seen.add(p)
                    unique_parts.append(p)
            
            if unique_parts:
                result = "\n\n".join(unique_parts)[:3000]
                logger.info(f"小红书提取成功，长度: {len(result)}")
                return result
                
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


# ============== Playwright 浏览器提取 (终极方案) ==============

_playwright_instance = None

async def _get_playwright():
    """获取或初始化 Playwright"""
    global _playwright_instance
    if _playwright_instance is None:
        try:
            from playwright.async_api import async_playwright
            _playwright_instance = await async_playwright().start()
        except Exception as e:
            logger.warning(f"Playwright 初始化失败: {e}")
            return None
    return _playwright_instance


# 在页面上下文中从 SPA 注入的全局 JSON 与 script 块解析文案（比 CSS 类名稳定）
# 避免把「最长字符串」选成 App 拉起配置等无关 JSON（如 dslVersion / launchApp）
_PLAYWRIGHT_EVAL_EXTRACT = """
() => {
  const MIN = 12;
  const JUNK_SUBSTR = /dslVersion|launchApp|tencentAppStore|wxopentag|universallink|jumpinstallurl|urlschema/i;
  const SKIP_KEYS = new Set([
    'strategies', 'launchApp', 'riskInfo', 'tracking', 'ads', 'report', 'abConfig',
  ]);
  function hasChinese(s) {
    for (let i = 0; i < s.length; i++) {
      const c = s.charCodeAt(i);
      if (c >= 0x4e00 && c <= 0x9fff) return true;
    }
    return false;
  }
  function isGarbage(s) {
    const t = (s || '').trim();
    if (t.length < MIN) return true;
    if (t.startsWith('{') || t.startsWith('[')) return true;
    if (JUNK_SUBSTR.test(t)) return true;
    return false;
  }
  function chineseNonTagChars(s) {
    let t = (s || '').replace(/#[^#\\n]+#/g, ' ').replace(/\\[话题\\]/g, '');
    let n = 0;
    for (let i = 0; i < t.length; i++) {
      const c = t.charCodeAt(i);
      if (c >= 0x4e00 && c <= 0x9fff) n++;
    }
    return n;
  }
  function score(s) {
    const body = chineseNonTagChars(s);
    const tags = (s.match(/#/g) || []).length;
    // 优先正文句子，避免只剩话题标签
    return body * 120 + tags * 8 + Math.min(s.length, 1500) * 0.05;
  }
  function walk(obj, parentKey, depth, out) {
    if (depth > 14 || obj == null) return;
    if (typeof obj === 'string') {
      const t = obj.trim();
      if (!isGarbage(t)) out.push(t);
      return;
    }
    if (Array.isArray(obj)) {
      for (const x of obj) walk(x, parentKey, depth + 1, out);
      return;
    }
    if (typeof obj === 'object') {
      for (const [k, v] of Object.entries(obj)) {
        if (SKIP_KEYS.has(k)) continue;
        walk(v, k, depth + 1, out);
      }
    }
  }
  function bestFromRoots() {
    const roots = [
      typeof window.__UNIVERSAL_DATA__ !== 'undefined' ? window.__UNIVERSAL_DATA__ : null,
      typeof window.__INITIAL_STATE__ !== 'undefined' ? window.__INITIAL_STATE__ : null,
      typeof window.__NEXT_DATA__ !== 'undefined' ? window.__NEXT_DATA__ : null,
    ];
    const candidates = [];
    for (const r of roots) {
      if (!r) continue;
      walk(r, '', 0, candidates);
    }
    let best = '';
    let bestSc = -1;
    for (const p of candidates) {
      const sc = score(p);
      if (sc > bestSc || (sc === bestSc && p.length > best.length)) {
        bestSc = sc;
        best = p;
      }
    }
    return best;
  }
  function fromScriptTags() {
    const scripts = document.querySelectorAll('script');
    const candidates = [];
    for (const s of scripts) {
      const t = (s.textContent || '').trim();
      if (t.length < 60) continue;
      try {
        const j = JSON.parse(t);
        walk(j, '', 0, candidates);
      } catch (e) { /* ignore */ }
    }
    let best = '';
    let bestSc = -1;
    for (const p of candidates) {
      const sc = score(p);
      if (sc > bestSc || (sc === bestSc && p.length > best.length)) {
        bestSc = sc;
        best = p;
      }
    }
    return best;
  }
  let text = bestFromRoots();
  const s2 = fromScriptTags();
  if (s2 && score(s2) > score(text)) text = s2;
  return text || '';
}
"""


async def extract_with_playwright(url: str, platform: Optional[str] = None) -> ExtractResult:
    """
    使用 Playwright 无头浏览器提取文本
    抖音/小红书为强 JS 站：优先从 window 级 JSON / 内联 script 解析，再回退 DOM / meta。
    """
    try:
        playwright = await _get_playwright()
        if not playwright:
            return ExtractResult(
                success=False,
                text="",
                method="playwright",
                error="Playwright 未安装或未初始化"
            )
        
        # 启动浏览器
        browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        
        try:
            context = await browser.new_context(
                user_agent=MOBILE_HEADERS["User-Agent"],
                viewport={"width": 375, "height": 812},
                device_scale_factor=2,
                locale="zh-CN",
            )
            
            page = await context.new_page()
            
            # 抖音/小红书长连接多，networkidle 易超时；先 DOM 再短暂等待脚本注入
            page.set_default_timeout(25000)
            
            logger.info(f"Playwright 访问: {url[:60]}...")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2.5)
            
            text = ""
            try:
                ev = await page.evaluate(_PLAYWRIGHT_EVAL_EXTRACT)
                if isinstance(ev, str) and len(ev.strip()) > 15:
                    text = ev.strip()
            except Exception as e:
                logger.debug(f"Playwright evaluate JSON 提取: {e}")
            
            if platform == "douyin":
                selectors = [
                    '[data-e2e="video-desc"]',
                    '[data-e2e="browse-video-desc"]',
                    '.video-info-title',
                    'h1',
                ]
                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            t2 = await element.text_content()
                            if t2 and len(t2.strip()) > len(text):
                                text = t2.strip()
                            if text and len(text) > 20:
                                break
                    except Exception:
                        continue
                        
            elif platform == "xiaohongshu":
                selectors = [
                    '#detail-desc',
                    '.note-content',
                    '[class*="desc"]',
                    'article',
                    'h1',
                ]
                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            t2 = await element.text_content()
                            if t2 and len(t2.strip()) > len(text):
                                text = t2.strip()
                            if text and len(text) > 20:
                                break
                    except Exception:
                        continue
            
            if not text or len(text) < 10:
                title = await page.title()
                meta_desc = await page.evaluate(
                    """() => {
                    const meta = document.querySelector('meta[name="description"]') ||
                        document.querySelector('meta[property="og:description"]');
                    return meta ? meta.content : '';
                }"""
                )
                parts = []
                if title and "抖音" not in title and "小红书" not in title:
                    parts.append(title)
                if meta_desc:
                    parts.append(meta_desc)
                text = "\n".join(parts)
            
            text = text.strip() if text else ""
            if platform == "xiaohongshu" and text:
                text = re.sub(r"^展开\s*", "", text).strip()
            
            if text and len(text) > 10:
                return ExtractResult(
                    success=True,
                    text=text[:12000],
                    method="playwright",
                    metadata={"platform": platform, "sub_method": "chromium_json_dom"}
                )
            return ExtractResult(
                success=False,
                text="",
                method="playwright",
                error="Playwright 未能提取到有效文本"
            )
                
        finally:
            await browser.close()
            
    except Exception as e:
        logger.warning(f"Playwright 提取失败: {e}")
        return ExtractResult(
            success=False,
            text="",
            method="playwright",
            error=f"Playwright 异常: {str(e)[:200]}"
        )


def _playwright_enabled() -> bool:
    """检查是否启用 Playwright"""
    v = os.environ.get("REMIX_PLAYWRIGHT_FALLBACK", "1").strip().lower()
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
    use_tikhub = _tikhub_in_chain()
    
    if prefer_method == "tikhub":
        strategies = [
            ("tikhub", lambda: extract_with_tikhub(resolved_url, platform)),
            ("web_scrape", lambda: extract_with_web_scrape(resolved_url, platform)),
            ("ytdlp", lambda: extract_with_ytdlp(resolved_url)),
            ("playwright", lambda: extract_with_playwright(resolved_url, platform)),
        ]
    elif prefer_method == "web_scrape":
        strategies = [
            ("web_scrape", lambda: extract_with_web_scrape(resolved_url, platform)),
        ]
        if use_tikhub:
            strategies.append(("tikhub", lambda: extract_with_tikhub(resolved_url, platform)))
        strategies.extend(
            [
                ("ytdlp", lambda: extract_with_ytdlp(resolved_url)),
                ("playwright", lambda: extract_with_playwright(resolved_url, platform)),
            ]
        )
    elif platform in ("douyin", "xiaohongshu"):
        # 抖音/小红书：不依赖第三方 API。顺序：轻量 Web → yt-dlp（抖音元数据常可用）→ Playwright（真实渲染 + JSON）→ 可选 TikHub
        strategies = [
            ("web_scrape", lambda: extract_with_web_scrape(resolved_url, platform)),
            ("ytdlp", lambda: extract_with_ytdlp(resolved_url)),
        ]
        if _playwright_enabled():
            strategies.append(("playwright", lambda: extract_with_playwright(resolved_url, platform)))
        if use_tikhub:
            strategies.append(("tikhub", lambda: extract_with_tikhub(resolved_url, platform)))
    else:
        # 其他平台：Web → 可选 TikHub → yt-dlp → Playwright
        strategies = [
            ("web_scrape", lambda: extract_with_web_scrape(resolved_url, platform)),
        ]
        if use_tikhub:
            strategies.append(("tikhub", lambda: extract_with_tikhub(resolved_url, platform)))
        strategies.append(("ytdlp", lambda: extract_with_ytdlp(resolved_url)))
        if _playwright_enabled():
            strategies.append(("playwright", lambda: extract_with_playwright(resolved_url, platform)))
    
    # 尝试每种策略
    errors = []
    for method_name, extractor_func in strategies:
        try:
            result = await extractor_func()
            if result.success and len(result.text) > 10:
                if result.method == "web_scrape" and _is_weak_web_extract(result.text, platform):
                    msg = (
                        f"web_scrape: 内容过短({len(result.text.strip())}字符)，"
                        f"已尝试后续策略（阈值 { _min_web_chars_for_platform(platform) }）"
                    )
                    errors.append(msg)
                    continue
                logger.info(f"提取成功: method={result.method}, length={len(result.text)}")
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
