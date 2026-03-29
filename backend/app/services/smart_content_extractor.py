"""
智能内容提取服务 - 方案A：标题+标签已够用

核心思路：
抖音视频的desc本身就是一句话标题+标签
我们基于此提供结构化的仿写素材，不需要完整的口播文字

提取目标：
- 纯净标题（去掉标签）
- 钩子：标题的核心吸引点
- 角度：内容的核心观点  
- 标签：话题标签
- 爆款元素：数字/身份/情绪等
- 内容类型：money/emotion/skill/life
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.services import tikhub_client
from app.services.link_resolver import resolve_any_url, detect_platform

logger = logging.getLogger(__name__)

# 简单内存缓存
_extract_cache: Dict[str, Dict] = {}
_CACHE_TTL = 3600  # 1小时


@dataclass
class ExtractedContent:
    """
    结构化提取结果 - 方案A（简化版）
    
    核心：标题 + 标签 → 结构化拆分
    """
    # 基础信息
    url: str
    platform: str
    video_id: str = ""
    author: str = ""
    
    # 核心内容
    original_title: str = ""      # 原始标题（含标签）
    title_clean: str = ""         # 纯净标题
    hook: str = ""                # 钩子
    body: str = ""                # 正文/角度
    tags: List[str] = field(default_factory=list)
    
    # 分类
    content_type: str = ""        # money/emotion/skill/life
    
    # 数据
    play_count: int = 0
    like_count: int = 0
    share_count: int = 0
    
    # 提取信息
    extract_method: str = ""
    extract_time: datetime = field(default_factory=datetime.utcnow)
    success: bool = False
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（API响应用）"""
        return {
            "success": self.success,
            "error": self.error,
            "url": self.url,
            "platform": self.platform,
            "video_id": self.video_id,
            "author": self.author,
            "original_title": self.original_title,
            "title_clean": self.title_clean,
            "hook": self.hook,
            "body": self.body,
            "tags": self.tags,
            "content_type": self.content_type,
            "stats": {
                "play_count": self.play_count,
                "like_count": self.like_count,
                "share_count": self.share_count
            },
            "extract_method": self.extract_method
        }


class SmartContentExtractor:
    """
    智能内容提取器 - 方案A
    
    策略：
    1. 优先TIKHub（成功率最高）
    2. 提取标题+标签，结构化拆分
    3. 不需要完整口播文字
    """
    
    def __init__(self):
        self.api_key = os.environ.get("TIKHUB_API_KEY", "").strip()
    
    async def extract(self, url: str, use_cache: bool = True) -> ExtractedContent:
        """提取内容主入口"""
        if not url or not url.strip():
            return ExtractedContent(
                url=url,
                platform="unknown",
                success=False,
                error="URL不能为空"
            )
        
        url = url.strip()
        
        # 检查缓存
        if use_cache:
            cache_key = self._get_cache_key(url)
            cached = _extract_cache.get(cache_key)
            if cached and (datetime.utcnow() - cached["time"]).seconds < _CACHE_TTL:
                return cached["data"]
        
        # 解析URL
        resolved_result = await resolve_any_url(url)
        if isinstance(resolved_result, dict):
            resolved_url = resolved_result.get("resolved_url", url)
        else:
            resolved_url = resolved_result
        
        platform = detect_platform(resolved_url)
        
        # 优先TIKHub
        if tikhub_client.is_configured():
            result = await self._extract_with_tikhub(resolved_url, platform)
            if result.success:
                self._save_to_cache(url, result)
                return result
        
        # 失败
        return ExtractedContent(
            url=url,
            platform=platform or "unknown",
            success=False,
            error="提取失败"
        )
    
    async def _extract_with_tikhub(
        self, 
        url: str, 
        platform: Optional[str]
    ) -> ExtractedContent:
        """使用TIKHub API提取"""
        
        try:
            # 抖音链接使用专用接口
            if platform == "douyin":
                try:
                    raw = await tikhub_client.fetch_douyin_web_one_video_by_share_url(url)
                    return self._parse_response(raw, url, platform)
                except Exception as e:
                    logger.warning(f"TIKHub抖音接口失败: {e}")
            
            return ExtractedContent(
                url=url,
                platform=platform or "unknown",
                success=False,
                error="不支持的平台或API失败"
            )
            
        except Exception as e:
            logger.error(f"TIKHub提取失败: {e}")
            return ExtractedContent(
                url=url,
                platform=platform or "unknown",
                success=False,
                error=f"TIKHub失败: {str(e)}"
            )
    
    def _parse_response(
        self, 
        data: Any, 
        url: str, 
        platform: Optional[str]
    ) -> ExtractedContent:
        """解析TIKHub响应为结构化数据"""
        
        result = ExtractedContent(
            url=url,
            platform=platform or "unknown",
            success=True,
            extract_method="tikhub_douyin"
        )
        
        if not data or not isinstance(data, dict):
            result.success = False
            result.error = "Empty response"
            return result
        
        # 解包嵌套数据
        data = self._unwrap_nested_data(data)
        
        # 基础信息
        result.video_id = str(data.get("aweme_id", ""))
        result.author = data.get("author", {}).get("nickname", "") if isinstance(data.get("author"), dict) else ""
        
        # 统计数据
        stats = data.get("statistics", {})
        result.play_count = stats.get("play_count", 0)
        result.like_count = stats.get("digg_count", stats.get("like_count", 0))
        result.share_count = stats.get("share_count", 0)
        
        # 核心：原始标题（含标签）
        original_title = data.get("desc", "")
        result.original_title = original_title
        
        # 提取标签
        text_extra = data.get("text_extra", [])
        result.tags = [
            tag.get("hashtag_name", "") 
            for tag in text_extra 
            if isinstance(tag, dict) and tag.get("hashtag_name")
        ]
        
        # 纯净标题（去掉标签）
        result.title_clean = self._clean_title(original_title)
        
        # 结构化拆分：hook + body
        result.hook, result.body = self._split_title_structure(result.title_clean)
        
        # 内容类型检测
        result.content_type = self._detect_content_type(result.title_clean, result.tags)
        
        return result
    
    def _unwrap_nested_data(self, data: Dict) -> Dict:
        """解包嵌套数据结构"""
        for key in ["aweme_detail", "aweme", "video", "data"]:
            if key in data and isinstance(data[key], dict):
                return {**data, **data[key]}
        return data
    
    def _clean_title(self, title: str) -> str:
        """清理标题：去掉标签，保留纯净文字"""
        # 去掉 #标签
        clean = re.sub(r'#\S+', '', title)
        # 去掉多余空格
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()
    
    def _split_title_structure(self, title: str) -> Tuple[str, str]:
        """
        拆分标题结构：钩子 + 角度
        
        抖音标题通常是：钩子（吸引点）+ 角度（内容点）
        例如：
        - "32岁，我终于活成了别人羡慕的样子" → 钩子：32岁终于...，角度：活成别人羡慕的样子
        - "从手心向上到月入3万：一个宝妈的3年私房创业史" → 钩子：从手心向上到月入3万，角度：宝妈3年创业史
        """
        if not title:
            return "", ""
        
        # 尝试用标点拆分
        if "：" in title or ":" in title:
            parts = re.split(r'[：:]', title, 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        
        if "，" in title or "," in title:
            parts = title.split("，") if "，" in title else title.split(",")
            if len(parts) >= 2:
                # 第一部分作为钩子，剩余作为角度
                return parts[0].strip(), "，".join(parts[1:]).strip()
        
        # 如果很短，整体作为钩子
        if len(title) <= 20:
            return title, ""
        
        # 默认：前20字作为钩子，剩余作为角度
        return title[:20], title[20:].strip()
    
    def _detect_content_type(self, title: str, tags: List[str]) -> str:
        """检测内容类型"""
        text = title + " " + " ".join(tags)
        text_lower = text.lower()
        
        # 搞钱类
        money_keywords = ["月入", "年入", "赚钱", "搞钱", "收入", "变现", "副业", "创业", "万", "利润"]
        if any(kw in text for kw in money_keywords):
            return "money"
        
        # 情感类
        emotion_keywords = ["逆袭", "终于", "感动", "心疼", "故事", "经历", "蜕变", "成长"]
        if any(kw in text for kw in emotion_keywords):
            return "emotion"
        
        # 技能类
        skill_keywords = ["教程", "方法", "技巧", "步骤", "攻略", "如何", "怎么", "学会"]
        if any(kw in text for kw in skill_keywords):
            return "skill"
        
        # 默认为生活类
        return "life"
    
    def _get_cache_key(self, url: str) -> str:
        """生成缓存key"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _save_to_cache(self, url: str, result: ExtractedContent):
        """保存到缓存"""
        cache_key = self._get_cache_key(url)
        _extract_cache[cache_key] = {
            "data": result,
            "time": datetime.utcnow()
        }


# ============== 便捷函数 ==============

_extractor: Optional[SmartContentExtractor] = None


def get_smart_extractor() -> SmartContentExtractor:
    """获取全局提取器实例"""
    global _extractor
    if _extractor is None:
        _extractor = SmartContentExtractor()
    return _extractor


async def extract_content(url: str, use_cache: bool = True) -> ExtractedContent:
    """便捷函数：提取内容"""
    extractor = get_smart_extractor()
    return await extractor.extract(url, use_cache)


async def extract_content_for_remix(url: str) -> Dict[str, Any]:
    """
    为仿写提取内容
    
    返回结构化的改写素材
    """
    result = await extract_content(url)
    return result.to_dict()
