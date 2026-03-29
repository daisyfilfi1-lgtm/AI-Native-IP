"""
抖音口播稿提取（主路径）：火山方舟豆包，支持两条 OpenAI 兼容路径：

1) **应用 Bot 对话**（推荐尝试「联网」）：`POST .../api/v3/bots/chat/completions`，`model` 为控制台应用 ID（如 bot-xxxx）。
   需在方舟控制台创建应用并开启联网/网页解析等插件；与裸推理接入点不同。
2) **推理接入点 Chat**：`POST .../api/v3/chat/completions`，`model` 为 ep-xxxx。

环境变量：
- ARK_API_KEY 或 DOUBAO_API_KEY（必填）
- ARK_BASE_URL（默认 https://ark.cn-beijing.volces.com/api/v3）
- ARK_MODEL / DOUBAO_MODEL：推理接入点 ID（ep-xxxx），用于路径 2
- ARK_BOT_ID / DOUBAO_BOT_ID：应用 Bot ID（bot-xxxx），用于路径 1
- REMIX_DOUYIN_ARK_BOT_FIRST：默认 1；为 1 且配置了 ARK_BOT_ID 时优先走 Bot，失败再回退 ep Chat（若配置了 ARK_MODEL）

在 Railway 上若 TikHub / ASR 不稳定，可只配置方舟；优先用带联网的 Bot 更接近「豆包里贴链接」的体验。

说明：路径 2 无法直接打开视频；路径 1 依赖控制台为应用开启联网等能力。仍会传入本地组装的页面/TikHub 摘录作为补充。
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Literal, Optional

logger = logging.getLogger(__name__)

_DEFAULT_ARK_BASE = "https://ark.cn-beijing.volces.com/api/v3"


def _ark_api_key() -> str:
    return os.environ.get("ARK_API_KEY", "").strip() or os.environ.get("DOUBAO_API_KEY", "").strip()


def _ark_chat_model() -> str:
    return os.environ.get("ARK_MODEL", "").strip() or os.environ.get("DOUBAO_MODEL", "").strip()


def _ark_bot_id() -> str:
    return os.environ.get("ARK_BOT_ID", "").strip() or os.environ.get("DOUBAO_BOT_ID", "").strip()


def is_doubao_configured() -> bool:
    """已配置方舟 Key，且至少具备推理接入点(ep)或应用 Bot(bot) 之一。"""
    key = _ark_api_key()
    return bool(key and (_ark_chat_model() or _ark_bot_id()))


def _ark_bot_first_enabled() -> bool:
    v = os.environ.get("REMIX_DOUYIN_ARK_BOT_FIRST", "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def _http_timeout_sec() -> float:
    timeout = 120.0
    raw = os.environ.get("OPENAI_HTTP_TIMEOUT", "").strip()
    if raw:
        try:
            timeout = max(30.0, float(raw))
        except ValueError:
            pass
    return timeout


def _ark_openai_chat_sync(
    system_prompt: str,
    user_prompt: str,
    *,
    endpoint: Literal["chat", "bot"],
) -> str:
    """endpoint=chat → /api/v3/chat/completions；endpoint=bot → /api/v3/bots/chat/completions。"""
    from openai import OpenAI

    key = _ark_api_key()
    root = (os.environ.get("ARK_BASE_URL", "").strip() or _DEFAULT_ARK_BASE).rstrip("/")
    if not key:
        return ""

    if endpoint == "bot":
        bot = _ark_bot_id()
        if not bot:
            return ""
        base = f"{root}/bots"
        model = bot
    else:
        model = _ark_chat_model()
        if not model:
            return ""
        base = root

    client = OpenAI(api_key=key, base_url=base, timeout=_http_timeout_sec())
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
) -> tuple[str, str]:
    """
    根据抖音链接与可选页面摘录，生成一段可仿写的口播文案（同步 API 在线程池执行）。
    若配置 ARK_BOT_ID 且 REMIX_DOUYIN_ARK_BOT_FIRST=1，优先调用应用 Bot（可含联网插件），失败再回退 ep Chat。

    返回 (正文, 端点标记)：端点为 \"bot\"、\"chat\" 或 \"\"（失败/未配置）。
    """
    if not is_doubao_configured():
        return "", ""

    system = (
        "任务：提取抖音视频文案（口播正文）。"
        "你是短视频口播文案整理助手。用户会提供抖音视频链接，以及从公开页面抓取到的标题与描述（可能不完整）。"
        "请根据这些信息，输出一段完整、可直接口播朗读的中文正文。"
        "不要输出标题、不要 markdown、不要列表符号、不要“如下”等套话。"
        "若摘录不足，可结合常见抖音口播结构做合理补全，但不得编造具体人名、数字与可验证事实。"
    )
    user = (
        "【提取抖音视频文案】\n\n"
        f"原始链接：{original_url}\n"
        f"解析后链接：{resolved_url}\n\n"
        f"以下为结构化素材（可能含用户粘贴、TikHub 元数据、页面摘录、ASR 等；请紧扣素材主题整理）：\n"
        f"{page_snippet or '（未能获取任何正文素材）'}\n\n"
        "请只输出一段口播稿正文："
    )

    def _run() -> tuple[str, str]:
        try:
            if _ark_bot_first_enabled() and _ark_bot_id():
                text = _ark_openai_chat_sync(system, user, endpoint="bot")
                if text:
                    return text, "bot"
                logger.info("方舟应用 Bot 未返回有效内容，尝试推理接入点 Chat")
            if _ark_chat_model():
                text = _ark_openai_chat_sync(system, user, endpoint="chat")
                return (text or ""), ("chat" if text else "")
            return "", ""
        except Exception as e:
            logger.warning("豆包口播稿生成失败: %s", e)
            return "", ""

    return await asyncio.to_thread(_run)
