"""
AI 服务统一调用：Embedding、LLM Chat、Whisper 转写。
支持 OpenAI 及兼容 API（如 Azure、国内代理）。
"""
import os
import tempfile
import urllib.request
from typing import Any
import json

from openai import OpenAI

from app.config.ai_config import get_ai_config

# 未配置 IP 术语表时使用的「内容语义」参考维与候选值（与 docs/TAG_TAXONOMY_REFERENCE.md 对齐）
REFERENCE_SEMANTIC_TAG_WHITELIST: dict[str, frozenset[str]] = {
    "theme_domain": frozenset(
        {
            "方法论与认知",
            "情感共情与价值观",
            "技术或产品展示",
            "团队实力",
            "美好生活展示",
            "个人经历和故事",
            "热点话题观点",
            "第三方对话",
            "其他",
        }
    ),
    "emotion_anchor": frozenset(
        {
            "愤怒",
            "焦虑",
            "希望",
            "共鸣",
            "猎奇",
            "认知深度",
            "娱乐",
            "其他",
        }
    ),
    "narrative_structure": frozenset(
        {
            "痛点开场",
            "故事反转",
            "干货清单",
            "对比论证",
            "反常识",
            "其他",
        }
    ),
    "persona_mode": frozenset(
        {
            "闺蜜吐槽",
            "专家科普",
            "经历分享",
            "旁观者观察",
            "自定义",
        }
    ),
}


def _get_text_client() -> OpenAI | None:
    """LLM / Embedding 使用的主客户端（可指向 DeepSeek 等）。"""
    cfg = get_ai_config()
    if not cfg.get("api_key"):
        return None
    kwargs: dict[str, Any] = {"api_key": cfg["api_key"]}
    if cfg.get("base_url"):
        kwargs["base_url"] = cfg["base_url"]
    return OpenAI(**kwargs)


def _get_transcription_client() -> OpenAI | None:
    """语音转写客户端；配置了 OPENAI_TRANSCRIPTION_API_KEY 时默认走 OpenAI 官方。"""
    cfg = get_ai_config()
    key = cfg.get("transcription_api_key")
    if not key:
        return None
    kwargs: dict[str, Any] = {"api_key": key}
    base = cfg.get("transcription_base_url")
    if base:
        kwargs["base_url"] = base
    return OpenAI(**kwargs)


def embed(texts: list[str]) -> list[list[float]] | None:
    """
    文本向量化。未配置时返回 None。
    """
    client = _get_text_client()
    if not client:
        return None
    cfg = get_ai_config()
    model = cfg.get("embedding_model") or "text-embedding-3-small"
    try:
        resp = client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
    except Exception:
        return None


def chat(
    messages: list[dict[str, str]],
    model: str | None = None,
) -> str | None:
    """
    LLM 对话。未配置或失败时返回 None。
    messages: [{"role": "user"|"system"|"assistant", "content": "..."}]
    """
    client = _get_text_client()
    if not client:
        return None
    cfg = get_ai_config()
    model = model or cfg.get("llm_model") or "gpt-4o-mini"
    try:
        resp = client.chat.completions.create(model=model, messages=messages)
        return (resp.choices[0].message.content or "").strip() or None
    except Exception:
        return None


def transcribe(audio_path: str) -> str | None:
    """
    Whisper 音频转文字。未配置或失败时返回 None。
    使用 OPENAI_TRANSCRIPTION_*（若配置）否则回退 OPENAI_*。
    audio_path: 本地文件路径。
    """
    client = _get_transcription_client()
    if not client:
        return None
    cfg = get_ai_config()
    model = cfg.get("whisper_model") or "whisper-1"
    try:
        with open(audio_path, "rb") as f:
            resp = client.audio.transcriptions.create(model=model, file=f)
        return (resp.text or "").strip() or None
    except Exception:
        return None


def transcribe_from_url(url: str) -> str | None:
    """
    从 URL 下载音视频并转写。未配置或失败时返回 None。
    支持常见音视频格式（依赖 Whisper/ffmpeg 支持）。
    """
    if not _get_transcription_client():
        return None
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
            tmp_path = tmp.name
        urllib.request.urlretrieve(url, tmp_path)
        return transcribe(tmp_path)
    except Exception:
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def suggest_tags_for_content(
    content: str,
    tag_categories: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """
    根据内容生成建议标签，供自动打标使用。
    - 若传入 tag_categories：严格按运营配置的术语表白名单输出。
    - 若未传入：使用内置「内容语义」参考维（见 REFERENCE_SEMANTIC_TAG_WHITELIST / docs/TAG_TAXONOMY_REFERENCE.md）。
    """
    cfg = get_ai_config()
    if not cfg.get("llm_available") or not cfg.get("auto_tag_enabled"):
        return None
    snippet = (content or "")[:800]
    if not snippet.strip():
        return None
    if tag_categories:
        # 使用运营配置的术语表进行受控打标：模型只能在候选项中选择。
        category_desc = []
        for c in tag_categories:
            values = c.get("values") or []
            enabled_values = [v.get("value") for v in values if v.get("enabled", True) and v.get("value")]
            if not enabled_values:
                continue
            field_name = c.get("type") or c.get("name")
            if not field_name:
                continue
            category_desc.append(
                {
                    "field": field_name,
                    "allowed_values": enabled_values,
                }
            )
        if not category_desc:
            return None

        prompt = """根据以下内容片段，从给定术语表中选择最匹配的标签并输出 JSON。
要求：
1) 只能使用术语表里的字段名和候选值，禁止自造字段和新值；
2) 每个字段最多输出 1 个值；
3) 无法判断就省略该字段；
4) 仅返回 JSON，不要 markdown 或解释。

术语表：
"""
        msg = (
            prompt
            + json.dumps(category_desc, ensure_ascii=False)
            + "\n\n内容：\n"
            + snippet
        )
    else:
        prompt = """根据以下内容片段，从下列「内容语义」维度中各选最匹配的一项，输出 JSON，仅返回 JSON，不要 markdown 或解释。
字段与候选值必须完全一致（不要自造新值）：
- theme_domain：方法论与认知 / 情感共情与价值观 / 技术或产品展示 / 团队实力 / 美好生活展示 / 个人经历和故事 / 热点话题观点 / 第三方对话 / 其他
- emotion_anchor：愤怒 / 焦虑 / 希望 / 共鸣 / 猎奇 / 认知深度 / 娱乐 / 其他
- narrative_structure：痛点开场 / 故事反转 / 干货清单 / 对比论证 / 反常识 / 其他
- persona_mode：闺蜜吐槽 / 专家科普 / 经历分享 / 旁观者观察 / 自定义
每个字段最多 1 个值；无法判断则省略该字段。

内容：
"""
        msg = prompt + snippet

    out = chat([{"role": "user", "content": msg}])
    if not out:
        return None
    try:
        out = out.strip()
        if out.startswith("```"):
            lines = out.split("\n")
            out = "\n".join(l for l in lines if not l.startswith("```"))
        parsed = json.loads(out)
        if not isinstance(parsed, dict):
            return None

        # 有术语表时，做一次白名单过滤，保证结果可直接落库使用
        if tag_categories:
            allowed_map: dict[str, set[str]] = {}
            for c in tag_categories:
                field_name = c.get("type") or c.get("name")
                if not field_name:
                    continue
                values = c.get("values") or []
                allowed_map[field_name] = {
                    v.get("value")
                    for v in values
                    if v.get("enabled", True) and v.get("value")
                }

            cleaned: dict[str, Any] = {}
            for k, v in parsed.items():
                if k not in allowed_map or not allowed_map[k]:
                    continue
                if isinstance(v, str) and v in allowed_map[k]:
                    cleaned[k] = v
            return cleaned or None

        cleaned_ref: dict[str, Any] = {}
        for k, v in parsed.items():
            allowed = REFERENCE_SEMANTIC_TAG_WHITELIST.get(k)
            if not allowed:
                continue
            if isinstance(v, str) and v in allowed:
                cleaned_ref[k] = v
        return cleaned_ref or None
    except Exception:
        return None
