"""
阿里云语音合成/识别服务
当前仅封装录音文件识别极速版（FlashRecognizer），适合 4 小时以内音频。
文档：https://help.aliyun.com/document_detail/90727.html
"""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import tempfile
import time
import urllib.parse
from typing import Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_ALIYUN_ASR_APPKEY = os.environ.get("ALIYUN_ASR_APPKEY", "").strip()
_ALIYUN_ASR_ACCESS_KEY_ID = os.environ.get("ALIYUN_ASR_ACCESS_KEY_ID", "").strip()
_ALIYUN_ASR_ACCESS_KEY_SECRET = os.environ.get("ALIYUN_ASR_ACCESS_KEY_SECRET", "").strip()

# Token 缓存（有效期约 10 小时，这里缓存 8 小时）
_token_cache: dict = {"token": "", "expires_at": 0}


def _is_configured() -> bool:
    return bool(_ALIYUN_ASR_APPKEY and _ALIYUN_ASR_ACCESS_KEY_ID and _ALIYUN_ASR_ACCESS_KEY_SECRET)


def _get_signature(string_to_sign: str, secret: str) -> str:
    h = hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1)
    return base64.b64encode(h.digest()).decode("utf-8")


async def _get_token() -> str:
    """获取阿里云 NLS Token（带缓存）"""
    global _token_cache
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 300:
        return _token_cache["token"]

    if not _is_configured():
        raise RuntimeError("阿里云 ASR 未配置")

    # 构造 POP 签名（STS 风格）
    ak_id = _ALIYUN_ASR_ACCESS_KEY_ID
    ak_secret = _ALIYUN_ASR_ACCESS_KEY_SECRET
    version = "2019-02-28"
    action = "CreateToken"
    region = "cn-shanghai"
    product = "nls-meta"

    params = {
        "Format": "JSON",
        "Version": version,
        "AccessKeyId": ak_id,
        "SignatureMethod": "HMAC-SHA1",
        "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "SignatureVersion": "1.0",
        "SignatureNonce": str(int(now * 1000)),
        "Action": action,
        "RegionId": region,
    }

    sorted_params = sorted(params.items())
    canonical_query = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in sorted_params)
    string_to_sign = f"GET&%2F&{quote(canonical_query, safe='')}"
    signature = _get_signature(string_to_sign, ak_secret + "&")
    # HMAC-SHA1 签名需要 base64 后再 urlencode
    signature = urllib.parse.quote(signature, safe='')

    url = f"https://nls-meta.cn-shanghai.aliyuncs.com/?{canonical_query}&Signature={signature}"

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()

    token_info = data.get("Token", {})
    token = token_info.get("Id")
    expire_time = token_info.get("ExpireTime")
    if not token:
        raise RuntimeError(f"获取阿里云 Token 失败: {data}")

    _token_cache["token"] = token
    _token_cache["expires_at"] = int(expire_time) if expire_time else int(now + 28800)
    logger.info("阿里云 ASR Token 刷新成功，有效期至 %s", _token_cache["expires_at"])
    return token


async def recognize_flash(audio_path: str) -> str:
    """
    阿里云录音文件识别极速版（FlashRecognizer）。
    直接上传本地音频文件，返回识别文本。
    """
    if not _is_configured():
        raise RuntimeError("阿里云 ASR 未配置（ALIYUN_ASR_APPKEY / ACCESS_KEY_ID / ACCESS_KEY_SECRET）")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    token = await _get_token()
    appkey = _ALIYUN_ASR_APPKEY

    # 根据文件后缀推断格式
    ext = os.path.splitext(audio_path)[1].lower().lstrip(".")
    if ext in ("mp3", "wav", "m4a", "ogg", "aac", "flac"):
        audio_format = ext
    else:
        audio_format = "mp3"

    url = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/FlashRecognizer"
    params = {
        "appkey": appkey,
        "format": audio_format,
        "sample_rate": 16000,
        "enable_punctuation_prediction": True,
        "enable_inverse_text_normalization": True,
    }
    headers = {
        "X-NLS-Token": token,
        "Content-Type": "application/octet-stream",
    }

    with open(audio_path, "rb") as f:
        audio_data = f.read()

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, params=params, content=audio_data)
        r.raise_for_status()
        result = r.json()

    status = result.get("status")
    if status != 20000000:
        err_msg = result.get("message", "未知错误")
        raise RuntimeError(f"阿里云 ASR 识别失败 [{status}]: {err_msg}")

    sentences = result.get("flash_result", {}).get("sentences", [])
    texts = [s.get("text", "").strip() for s in sentences if s.get("text")]
    return " ".join(texts)


async def extract_audio_to_text(audio_path: str) -> str:
    """便捷函数：音频文件 → 口播文本"""
    return await recognize_flash(audio_path)
