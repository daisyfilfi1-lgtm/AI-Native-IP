"""
AI 服务配置：从环境变量读取，支持 OpenAI 及兼容 API。

支持「文本 LLM + Embedding」与「语音转写」使用不同厂商：
- 主密钥 OPENAI_* 可指向 DeepSeek 等兼容端点
- 可选 OPENAI_TRANSCRIPTION_* 专用于 Whisper（官方 OpenAI）
"""
import os
from typing import Any

# OpenAI 官方 API 默认 Base（仅用于转写独立客户端未显式填 base_url 时）
_DEFAULT_OPENAI_TRANSCRIPTION_BASE = "https://api.openai.com/v1"


def get_ai_config() -> dict[str, Any]:
    """
    返回 AI 配置字典。未配置时对应值为 None，调用方需判断。
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or None
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small").strip()
    llm_model = os.environ.get("LLM_MODEL", "gpt-4o-mini").strip()
    auto_tag_enabled = os.environ.get("AUTO_TAG_ENABLED", "true").lower() in ("true", "1", "yes")

    # 语音转写：未配置时回退到主 OPENAI_*（全 OpenAI 场景）
    trans_key = os.environ.get("OPENAI_TRANSCRIPTION_API_KEY", "").strip() or None
    trans_base = os.environ.get("OPENAI_TRANSCRIPTION_BASE_URL", "").strip() or None
    whisper_model = os.environ.get("WHISPER_MODEL", "whisper-1").strip() or "whisper-1"

    effective_trans_key = trans_key or api_key
    # 若显式配置了转写专用 Key，默认走官方 OpenAI（DeepSeek 等无 Whisper）
    if trans_key and not trans_base:
        trans_base = _DEFAULT_OPENAI_TRANSCRIPTION_BASE
    if not trans_key:
        trans_base = trans_base or base_url

    return {
        "api_key": api_key,
        "base_url": base_url,
        "embedding_model": embedding_model,
        "llm_model": llm_model,
        "auto_tag_enabled": auto_tag_enabled,
        "embedding_available": bool(api_key),
        "llm_available": bool(api_key),
        # 转写
        "transcription_api_key": effective_trans_key,
        "transcription_base_url": trans_base,
        "whisper_model": whisper_model,
        "transcription_available": bool(effective_trans_key),
    }


def is_llm_configured() -> bool:
    """LLM 是否已配置（可调用 chat）。"""
    return bool(get_ai_config().get("api_key"))
