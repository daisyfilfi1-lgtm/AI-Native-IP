"""
AI 服务统一调用：Embedding、LLM Chat、Whisper 转写。
支持 OpenAI 及兼容 API、Cohere Embedding、本地模型作为 fallback。
"""
import os
import tempfile
import urllib.request
from typing import Any
import json
import logging

from openai import OpenAI

from app.config.ai_config import get_ai_config

logger = logging.getLogger(__name__)

# Cohere 配置
_COHERE_CONFIG = None

def _get_cohere_config():
    """获取Cohere配置"""
    global _COHERE_CONFIG
    if _COHERE_CONFIG is None:
        api_key = os.environ.get("COHERE_API_KEY", "").strip() or None
        _COHERE_CONFIG = {
            "api_key": api_key,
            "enabled": bool(api_key)
        }
    return _COHERE_CONFIG

def _embed_cohere(texts: list[str]) -> list[list[float]] | None:
    """Cohere Embedding - 支持多语言，免费5000次/月"""
    import cohere
    
    cfg = _get_cohere_config()
    if not cfg.get("enabled"):
        return None
    
    try:
        client = cohere.Client(cfg["api_key"])
        response = client.embed(
            texts=texts,
            model='embed-multilingual-v3.0',
            input_type='search_document'
        )
        # Handle both list and array formats
        embeddings = response.embeddings
        if hasattr(embeddings[0], 'tolist'):
            return [emb.tolist() for emb in embeddings]
        return embeddings
    except Exception as e:
        logger.warning(f"Cohere embedding failed: {e}")
        return None

# 腾讯云配置
_TENCENT_CLOUD_CONFIG = None

def _get_tencent_config():
    """获取腾讯云配置"""
    global _TENCENT_CLOUD_CONFIG
    if _TENCENT_CLOUD_CONFIG is None:
        secret_id = os.environ.get("TENCENT_CLOUD_SECRET_ID", "").strip() or None
        secret_key = os.environ.get("TENCENT_CLOUD_SECRET_KEY", "").strip() or None
        _TENCENT_CLOUD_CONFIG = {
            "secret_id": secret_id,
            "secret_key": secret_key,
            "enabled": bool(secret_id and secret_key)
        }
    return _TENCENT_CLOUD_CONFIG

def _tencentcloud_sign(secret_key: str, date: str, service: str, string_to_sign: str) -> str:
    """TC3-HMAC-SHA256 签名"""
    import hashlib
    import hmac
    def tc3_hash(key, msg):
        return hmac.new(key.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    secret_date = tc3_hash(secret_key, date)
    secret_service = tc3_hash(secret_date, service)
    secret_signing = tc3_hash(secret_service, 'tc3_request')
    return hmac.new(secret_signing.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

def _embed_tencentcloud(texts: list[str]) -> list[list[float]] | None:
    """腾讯云混元Embedding"""
    import hashlib
    import time
    from datetime import datetime
    import requests
    
    cfg = _get_tencent_config()
    if not cfg.get("enabled"):
        return None
    
    secret_id = cfg["secret_id"]
    secret_key = cfg["secret_key"]
    
    timestamp = int(time.time())
    
    # 使用文本 embedding 接口
    payload = {
        'TextList': texts,
        'Model': 'embedding-equation-7b-v1'
    }
    
    service = 'hunyuan'
    action = 'GetEmbedding'
    version = '2023-09-01'
    region = 'ap-guangzhou'
    
    # 构建签名
    http_request_method = 'POST'
    canonical_uri = '/'
    canonical_query_string = ''
    payload_str = json.dumps(payload, ensure_ascii=False)
    hashed_request_payload = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
    canonical_headers = 'content-type:application/json;host:hunyuan.tencentcloudapi.com\n'
    signed_headers = 'content-type;host'
    canonical_request = f'{http_request_method}\n{canonical_uri}\n{canonical_query_string}\n{canonical_headers}\nsigned_headers:{signed_headers}\nhashed_request_payload:{hashed_request_payload}'
    
    algorithm = 'TC3-HMAC-SHA256'
    date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
    credential_scope = f'{date}/{service}/tc3_request'
    hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
    string_to_sign = f'{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}'
    
    signature = _tencentcloud_sign(secret_key, date, service, string_to_sign)
    authorization = f'{algorithm} Credential={secret_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': authorization,
        'Host': 'hunyuan.tencentcloudapi.com',
        'X-TC-Action': action,
        'X-TC-Version': version,
        'X-TC-Timestamp': str(timestamp),
        'X-TC-Region': region
    }
    
    try:
        resp = requests.post('https://hunyuan.tencentcloudapi.com', headers=headers, json=payload, timeout=60)
        result = resp.json()
        if 'Response' in result and 'EmbeddingList' in result.get('Response', {}):
            embeddings = []
            for item in result['Response']['EmbeddingList']:
                embeddings.append(item['Embedding'])
            logger.info(f"Tengtcent Cloud embedding success: {len(embeddings)} vectors")
            return embeddings
        else:
            logger.warning(f"Tengtcent Cloud embedding failed: {result}")
            return None
    except Exception as e:
        logger.error(f"Tengtcent Cloud embedding error: {e}")
        return None

# 本地embedding模型（当API不可用时的fallback）
_LOCAL_EMBEDDING_MODEL = None
_LOCAL_EMBEDDING_DIM = 768  # 默认维度

def _get_local_embedding_model():
    """获取本地embedding模型（延迟加载）- 尝试多种方式。

    默认 **不** 加载：sentence-transformers + PyTorch 可达数百 MB～数 GB，Railway 等小内存实例在
    API 临时失败时若误走本地 fallback 会整进程 OOM（日志仅显示 Killed）。
    仅当显式设置 LOCAL_EMBEDDING_ENABLED=true 时才尝试加载。
    """
    global _LOCAL_EMBEDDING_MODEL
    if os.environ.get("LOCAL_EMBEDDING_ENABLED", "").lower() not in ("1", "true", "yes"):
        return None
    if _LOCAL_EMBEDDING_MODEL is None:
        # 方式1: sentence-transformers (需要torch)
        try:
            from sentence_transformers import SentenceTransformer
            model_name = os.environ.get("LOCAL_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
            _LOCAL_EMBEDDING_MODEL = SentenceTransformer(model_name, device='cpu')
            logger.info(f"Loaded local embedding model: {model_name}")
            return _LOCAL_EMBEDDING_MODEL
        except Exception as e1:
            logger.warning(f"sentence-transformers failed: {e1}")
        
        # 方式2: 直接用transformers (不用torch)
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            model_name = os.environ.get("LOCAL_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name)
            model.eval()
            _LOCAL_EMBEDDING_MODEL = {"tokenizer": tokenizer, "model": model}
            logger.info(f"Loaded embedding model via transformers: {model_name}")
            return _LOCAL_EMBEDDING_MODEL
        except Exception as e2:
            logger.warning(f"transformers direct also failed: {e2}")
        
        _LOCAL_EMBEDDING_MODEL = False
    return _LOCAL_EMBEDDING_MODEL if _LOCAL_EMBEDDING_MODEL else None


def _embed_with_local_model(texts: list[str], model_info) -> list[list[float]] | None:
    """使用本地模型生成embedding"""
    try:
        # sentence-transformers方式
        if hasattr(model_info, 'encode'):
            embeddings = model_info.encode(texts, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]
        # transformers直接方式
        elif isinstance(model_info, dict):
            tokenizer = model_info["tokenizer"]
            model = model_info["model"]
            import torch
            encoded = tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
            with torch.no_grad():
                outputs = model(**encoded)
                # Mean pooling
                embeddings = outputs.last_hidden_state.mean(dim=1).numpy()
            return [emb.tolist() for emb in embeddings]
    except Exception as e:
        logger.error(f"Local embedding failed: {e}")
    return None

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


def _http_timeout_seconds() -> float:
    """LLM / Embedding / 转写 HTTP 超时（秒），避免长时间挂起占满 worker。"""
    raw = os.environ.get("OPENAI_HTTP_TIMEOUT", "120").strip()
    try:
        return max(10.0, float(raw))
    except ValueError:
        return 120.0


def _get_text_client() -> OpenAI | None:
    """LLM / Embedding 使用的主客户端（可指向 DeepSeek 等）。"""
    cfg = get_ai_config()
    if not cfg.get("api_key"):
        return None
    kwargs: dict[str, Any] = {
        "api_key": cfg["api_key"],
        "timeout": _http_timeout_seconds(),
    }
    if cfg.get("base_url"):
        kwargs["base_url"] = cfg["base_url"]
    return OpenAI(**kwargs)


def _get_transcription_client() -> OpenAI | None:
    """语音转写客户端；配置了 OPENAI_TRANSCRIPTION_API_KEY 时默认走 OpenAI 官方。"""
    cfg = get_ai_config()
    key = cfg.get("transcription_api_key")
    if not key:
        return None
    kwargs: dict[str, Any] = {"api_key": key, "timeout": _http_timeout_seconds()}
    base = cfg.get("transcription_base_url")
    if base:
        kwargs["base_url"] = base
    return OpenAI(**kwargs)


def embed(texts: list[str]) -> list[list[float]] | None:
    """
    文本向量化。优先级：
    1. Cohere（若配置 COHERE_API_KEY）
    2. 腾讯云混元（若配置 TENCENT_CLOUD_*）
    3. OpenAI 兼容 API（OPENAI_API_KEY）
    4. 本地模型（仅当 LOCAL_EMBEDDING_ENABLED=true，避免 Railway 误加载 PyTorch OOM）
    5. 无向量 - 纯文本存储
    """
    # 1. 优先尝试 Cohere
    cohere_result = _embed_cohere(texts)
    if cohere_result:
        return cohere_result
    
    # 2. 腾讯云
    tencent_result = _embed_tencentcloud(texts)
    if tencent_result:
        return tencent_result
    
    # 2. 尝试OpenAI API
    client = _get_text_client()
    if client:
        cfg = get_ai_config()
        model = cfg.get("embedding_model") or "text-embedding-3-small"
        try:
            resp = client.embeddings.create(input=texts, model=model)
            return [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
        except Exception as e:
            logger.warning(f"OpenAI embedding failed: {e}")
    
    # 3. Fallback: 尝试本地模型
    local_model = _get_local_embedding_model()
    if local_model:
        result = _embed_with_local_model(texts, local_model)
        if result:
            return result
    
    # 都失败时返回None，让调用方处理
    logger.warning("All embedding methods failed - will store text without vectors")
    return None


def embed_texts_batched(
    texts: list[str],
    *,
    batch_size: int = 16,
) -> list[list[float] | None]:
    """
    批量向量化，与输入等长；失败项为 None。单批失败时回退为逐条请求，降低大任务 OOM。
    """
    if not texts:
        return []
    out: list[list[float] | None] = [None] * len(texts)
    bs = max(1, batch_size)
    for i in range(0, len(texts), bs):
        batch = texts[i : i + bs]
        vecs = embed(batch)
        if vecs and len(vecs) == len(batch):
            for j, v in enumerate(vecs):
                out[i + j] = v
            continue
        for j, t in enumerate(batch):
            one = embed([t])
            if one and one[0]:
                out[i + j] = one[0]
    return out


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

