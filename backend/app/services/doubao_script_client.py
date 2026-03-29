"""
抖音口播稿提取（主路径）：火山方舟豆包（OpenAI 兼容 Chat API）根据链接 + 页面摘录生成口播稿。

在 Railway 上若 TikHub / 下载+ASR / Whisper 不稳定，可只配置豆包作为抖音唯一提取方式。

环境变量（与火山引擎控制台「推理接入点」一致）：
- ARK_API_KEY 或 DOUBAO_API_KEY
- ARK_BASE_URL（默认 https://ark.cn-beijing.volces.com/api/v3）
- ARK_MODEL 或 DOUBAO_MODEL：推理接入点 ID（如 ep-xxxx）

说明：模型无法直接「打开」视频；会先尽量抓取页面可见标题/描述，再交给豆包整理成口播正文。
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_ARK_BASE = "https://ark.cn-beijing.volces.com/api/v3"


def is_doubao_configured() -> bool:
    key = os.environ.get("ARK_API_KEY", "").strip() or os.environ.get("DOUBAO_API_KEY", "").strip()
    model = os.environ.get("ARK_MODEL", "").strip() or os.environ.get("DOUBAO_MODEL", "").strip()
    return bool(key and model)


def _doubao_chat_sync(
    system_prompt: str,
    user_prompt: str,
) -> str:
    from openai import OpenAI

    key = os.environ.get("ARK_API_KEY", "").strip() or os.environ.get("DOUBAO_API_KEY", "").strip()
    base = (
        os.environ.get("ARK_BASE_URL", "").strip() or _DEFAULT_ARK_BASE
    ).rstrip("/")
    model = os.environ.get("ARK_MODEL", "").strip() or os.environ.get("DOUBAO_MODEL", "").strip()
    if not key or not model:
        return ""

    timeout = 120.0
    raw = os.environ.get("OPENAI_HTTP_TIMEOUT", "").strip()
    if raw:
        try:
            timeout = max(30.0, float(raw))
        except ValueError:
            pass

    client = OpenAI(api_key=key, base_url=base, timeout=timeout)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.35,
        max_tokens=4096,
    )
    choice = resp.choices[0].message
    return (choice.content or "").strip()


async def douyin_script_via_doubao(
    resolved_url: str,
    original_url: str,
    page_snippet: str,
) -> str:
    """
    根据抖音链接与可选页面摘录，生成一段可仿写的口播文案（同步 API 在线程池执行）。
    """
    if not is_doubao_configured():
        return ""

    system = (
        "你是短视频口播文案整理助手。用户会提供抖音视频链接，以及从公开页面抓取到的标题与描述（可能不完整）。"
        "请根据这些信息，输出一段完整、可直接口播朗读的中文正文。"
        "不要输出标题、不要 markdown、不要列表符号、不要“如下”等套话。"
        "若摘录不足，可结合常见抖音口播结构做合理补全，但不得编造具体人名、数字与可验证事实。"
    )
    user = (
        f"原始链接：{original_url}\n"
        f"解析后链接：{resolved_url}\n\n"
        f"页面可见文字摘录：\n{page_snippet or '（未能抓取到页面正文）'}\n\n"
        "请只输出一段口播稿正文："
    )

    def _run() -> str:
        try:
            return _doubao_chat_sync(system, user)
        except Exception as e:
            logger.warning("豆包口播稿生成失败: %s", e)
            return ""

    return await asyncio.to_thread(_run)
