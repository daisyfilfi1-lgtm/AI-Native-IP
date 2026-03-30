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

    主密钥：OPENAI_API_KEY（任意 OpenAI 兼容厂商）；
    若仅使用 Google Gemini，可只配置 GEMINI_API_KEY（与 OPENAI_API_KEY 二选一，等价）。
    端点示例（Gemini OpenAI 兼容）：
    OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
    """
    api_key = (
        os.environ.get("OPENAI_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
        or None
    )
    base_url = (
        os.environ.get("OPENAI_BASE_URL", "").strip()
        or os.environ.get("GEMINI_BASE_URL", "").strip()
        or None
    )
    embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small").strip()
    # 未设置时默认 gpt-4o-mini；使用 Gemini 时请在环境变量设置 LLM_MODEL（如 gemini-2.0-flash）
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


# Gemini OpenAI 兼容官方端点（仅当 FEEDBACK_LLM_MODEL 为 gemini 且未显式填 base 时使用）
_GEMINI_OPENAI_COMPAT_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"


def get_feedback_llm_config() -> dict[str, Any]:
    """
    多轮对话反馈专用：改写稿件、总结学习要点（与主站 LLM_MODEL 解耦）。

    若未设置 FEEDBACK_LLM_MODEL，返回空 dict，表示走主 LLM（get_ai_config）。

    推荐与主模型分离时配置：
    - FEEDBACK_LLM_MODEL=gemini-2.0-flash（或其它 gemini-*）
    - FEEDBACK_LLM_API_KEY=（Gemini API Key，可与 GEMINI_API_KEY 二选一）
    - FEEDBACK_LLM_BASE_URL=（可选；未填且模型名含 gemini 时自动使用 Google OpenAI 兼容端点）
    """
    model = os.environ.get("FEEDBACK_LLM_MODEL", "").strip()
    if not model:
        return {}
    key = (
        os.environ.get("FEEDBACK_LLM_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
        or None
    )
    base = (
        os.environ.get("FEEDBACK_LLM_BASE_URL", "").strip()
        or os.environ.get("GEMINI_BASE_URL", "").strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or None
    )
    ml = model.lower()
    if not base and ("gemini" in ml):
        base = _GEMINI_OPENAI_COMPAT_BASE
    return {
        "llm_model": model,
        "api_key": key,
        "base_url": base,
    }


def is_feedback_llm_configured() -> bool:
    """反馈链路是否已单独配置可用（有模型名且有 Key）。"""
    fb = get_feedback_llm_config()
    return bool(fb.get("llm_model") and fb.get("api_key"))
