"""
链接 → 仿写信源文本（新版）
使用统一的文本提取服务
"""
import logging
from typing import Any, Dict

from app.services.text_extractor import extract_text, ExtractResult
from app.services.link_resolver import resolve_any_url

logger = logging.getLogger(__name__)


async def extract_competitor_text_with_fallback(url: str) -> Dict[str, Any]:
    """
    带诊断信息的竞品文本提取（主入口）
    
    返回:
        {
            "success": bool,
            "text": str,
            "error": str,
            "method": str,
            "metadata": dict,
        }
    """
    if not url or not url.strip():
        return {
            "success": False,
            "text": "",
            "error": "链接不能为空",
            "method": "none",
            "metadata": {},
        }
    
    # 使用统一的提取服务
    result: ExtractResult = await extract_text(url.strip())
    
    return {
        "success": result.success,
        "text": result.text,
        "error": result.error,
        "method": result.method,
        "metadata": result.metadata,
    }


async def extract_competitor_text_for_remix(url: str) -> str:
    """
    兼容旧接口的提取函数
    成功返回文本，失败返回空字符串（不推荐在新代码中使用）
    """
    result = await extract_competitor_text_with_fallback(url)
    return result["text"] if result["success"] else ""


# 为了保持兼容性，保留旧函数名
resolve_short_url = resolve_any_url


def build_fallback_text(url: str) -> str:
    """兜底方案（保留用于兼容）"""
    return f"无法从链接提取内容，请检查链接是否有效: {url[:100]}"
