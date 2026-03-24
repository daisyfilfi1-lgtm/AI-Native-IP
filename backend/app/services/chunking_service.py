"""
智能分块服务 - 提供多种分块策略

优化内容：
- P1: 递归分块（按段落→句子→词递减）
- P3: 父子文档索引（保存父文档引用）
"""
import re
import os
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Chunk:
    """分块结果"""
    content: str
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = None


# 默认分隔符列表（按优先级递减）
DEFAULT_SEPARATORS = [
    "\n\n",      # 段落分隔
    "\n",        # 换行
    "。",        # 中文句号
    ". ",        # 英文句号+空格
    "！",        # 中文感叹号
    "?",         # 英文问号
    "；",        # 中文分号
    "; ",        # 英文分号
    "，",        # 中文逗号
    ", ",        # 英文逗号
    " ",         # 空格
]


def _get_separators() -> List[str]:
    """获取配置的分隔符列表"""
    raw = os.environ.get("CHUNK_SEPARATORS", "").strip()
    if raw:
        return [s.replace("\\n", "\n").replace("\\t", "\t") for s in raw.split("|")]
    return DEFAULT_SEPARATORS


def _get_chunk_size() -> int:
    """获取分块大小"""
    raw = os.environ.get("CHUNK_CHUNK_SIZE", "").strip()
    if raw:
        try:
            return max(100, int(raw))
        except ValueError:
            pass
    return 1500  # 默认1500字符（约300-500tokens）


def _get_overlap() -> int:
    """获取重叠大小"""
    raw = os.environ.get("CHUNK_OVERLAP", "").strip()
    if raw:
        try:
            return max(0, min(500, int(raw)))
        except ValueError:
            pass
    return 100  # 默认100字符重叠


def _get_parent_chunk_size() -> int:
    """获取父文档块大小"""
    raw = os.environ.get("CHUNK_PARENT_SIZE", "").strip()
    if raw:
        try:
            return max(500, int(raw))
        except ValueError:
            pass
    return 5000  # 父文档5000字符


def recursive_chunk(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
    min_chunk_size: int = 100,
) -> List[Chunk]:
    """
    递归分块 - 按分隔符优先级依次拆分

    优点：
    - 保持语义完整性（不会在句子中间断开）
    - 适用于中英文混合文本
    - 可配置性强

    Args:
        text: 待分块文本
        chunk_size: 目标块大小（字符）
        overlap: 块之间重叠字符数
        min_chunk_size: 最小块大小

    Returns:
        List[Chunk]: 分块结果列表
    """
    if not text or not text.strip():
        return []

    chunk_size = chunk_size or _get_chunk_size()
    overlap = overlap or _get_overlap()
    separators = _get_separators()

    text = text.strip()
    chunks: List[Chunk] = []

    # 递归拆分函数
    def split_by_separators(txt: str, sep_idx: int) -> List[str]:
        """按分隔符递归拆分"""
        if len(txt) <= chunk_size:
            return [txt]

        if sep_idx >= len(separators):
            # 最细粒度也无法拆分，直接按固定长度切
            return _fixed_chunk(txt, chunk_size, overlap)

        sep = separators[sep_idx]
        parts = txt.split(sep)

        result = []
        current = ""

        for part in parts:
            test = current + sep + part if current else part
            if len(test) <= chunk_size:
                current = test
            else:
                if current:
                    result.append(current)
                    # 处理重叠
                    if overlap > 0 and len(current) > overlap:
                        overlap_text = current[-(overlap):]
                        current = overlap_text + sep + part if overlap_text else part
                    else:
                        current = part
                else:
                    # 当前片段本身就超长，递归用更细粒度
                    sub_parts = split_by_separators(part, sep_idx + 1)
                    result.extend(sub_parts)
                    current = ""

        if current:
            result.append(current)

        return result

    def _fixed_chunk(txt: str, size: int, ov: int) -> List[str]:
        """固定长度分块（保底方案）"""
        result = []
        start = 0
        while start < len(txt):
            end = min(start + size, len(txt))
            result.append(txt[start:end].strip())
            start = end - ov
            if start >= len(txt):
                break
        return [r for r in result if r]

    # 执行分块
    raw_chunks = split_by_separators(text, 0)

    # 过滤空块并添加元数据
    for i, chunk_text in enumerate(raw_chunks):
        if len(chunk_text.strip()) >= min_chunk_size:
            chunks.append(Chunk(
                content=chunk_text.strip(),
                metadata={"chunk_index": i, "strategy": "recursive"}
            ))

    return chunks


def parent_document_chunk(
    text: str,
    parent_size: int = None,
    child_size: int = None,
    overlap: int = None,
) -> Tuple[List[Chunk], List[Chunk]]:
    """
    父子文档分块 - 同时返回父块和子块

    P3: 父文档索引实现

    优点：
    - 精确检索：子块用于向量检索
    - 完整上下文：父块用于最终生成

    Args:
        text: 待分块文本
        parent_size: 父块大小
        child_size: 子块大小
        overlap: 重叠大小

    Returns:
        (parents, children): 父块列表和子块列表
    """
    parent_size = parent_size or _get_parent_chunk_size()
    child_size = child_size or _get_chunk_size()
    overlap = overlap or _get_overlap()

    if not text or not text.strip():
        return [], []

    text = text.strip()

    # 先按父块大小拆分
    parent_chunks: List[Chunk] = []
    parents = recursive_chunk(text, parent_size, overlap, min_chunk_size=parent_size // 2)

    for i, parent in enumerate(parents):
        parent_id = f"parent_{i}_{hash(text[:20])}"
        parent_chunk = Chunk(
            content=parent.content,
            metadata={"type": "parent", "parent_index": i}
        )
        parent_chunks.append(parent_chunk)

        # 对每个父块再细分为子块
        children = recursive_chunk(parent.content, child_size, overlap, min_chunk_size=100)
        for j, child in enumerate(children):
            child_chunk = Chunk(
                content=child.content,
                parent_id=parent_id,
                metadata={
                    "type": "child",
                    "parent_index": i,
                    "child_index": j,
                    "total_children": len(children)
                }
            )
            parent_chunks.append(child_chunk)

    return parent_chunks


def hybrid_chunk(
    text: str,
    max_chunks: int = 80,
) -> List[Chunk]:
    """
    混合分块策略 - 自动选择最佳分块方式

    智能选择：
    - 短文本（<3000字符）：不拆分，直接作为单一块
    - 中等文本（3000-10000）：递归分块
    - 长文本（>10000）：父子分块

    Args:
        text: 待分块文本
        max_chunks: 最大分块数

    Returns:
        List[Chunk]: 分块结果
    """
    if not text:
        return []

    text = text.strip()
    text_len = len(text)

    if text_len < 3000:
        # 短文本不拆分
        return [Chunk(content=text, metadata={"strategy": "none", "length": text_len})]

    if text_len < 10000:
        # 中等文本用递归分块
        chunks = recursive_chunk(text)
    else:
        # 长文本用父子分块
        parents, children = parent_document_chunk(text)
        # 返回子块（用于检索），但保留parent_id引用
        chunks = [c for c in parents if c.metadata.get("type") == "child"]
        if not children:
            chunks = parents

    # 限制最大块数
    if len(chunks) > max_chunks:
        # 均匀采样
        step = len(chunks) / max_chunks
        chunks = [chunks[int(i * step)] for i in range(max_chunks)]

    return chunks


# 兼容旧接口
def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    兼容旧接口 - 返回简单字符串列表
    """
    chunks = recursive_chunk(text, chunk_size, overlap)
    return [c.content for c in chunks]
