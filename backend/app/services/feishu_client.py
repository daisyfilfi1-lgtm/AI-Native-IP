"""
飞书开放平台 API 客户端：tenant token、知识空间列表、节点列表、文档纯文本。
需应用权限：wiki:space:read、wiki:node:read、wiki:wiki；获取文档内容需 doc 相关权限（见 README）。
"""
import os
import time
from typing import Any, Iterator

import requests

BASE = "https://open.feishu.cn/open-apis"

_token_cache: dict = {}  # (app_id, app_secret) -> (token, expire_ts)


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    """获取 tenant_access_token，带简单内存缓存。"""
    key = (app_id, app_secret)
    now = time.time()
    if key in _token_cache:
        tok, exp = _token_cache[key]
        if exp > now + 60:
            return tok
    r = requests.post(
        f"{BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu token error: {data}")
    token = data["tenant_access_token"]
    # 过期时间秒数，提前 5 分钟刷新
    _token_cache[key] = (token, now + data.get("expire", 7200) - 300)
    return token


def list_spaces(token: str, page_size: int = 50) -> list[dict]:
    """获取知识空间列表（分页拉全）。"""
    out: list[dict] = []
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        r = requests.get(
            f"{BASE}/wiki/v2/spaces",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu list spaces error: {data}")
        items = data.get("data", {}).get("items") or []
        out.extend(items)
        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token")
        if not page_token:
            break
    return out


def list_nodes(
    token: str,
    space_id: str,
    parent_node_token: str | None = None,
    page_size: int = 50,
) -> Iterator[dict]:
    """分页获取知识空间下子节点列表。"""
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        if parent_node_token:
            params["parent_node_token"] = parent_node_token
        r = requests.get(
            f"{BASE}/wiki/v2/spaces/{space_id}/nodes",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu list nodes error: {data}")
        items = data.get("data", {}).get("items") or []
        for item in items:
            yield item
        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token")
        if not page_token:
            break


def get_doc_raw_content(token: str, obj_type: str, obj_token: str) -> str:
    """
    获取文档纯文本。支持旧版 doc；新版 docx 需文档权限。
    失败时抛出 RuntimeError（含 code/msg），便于调用方记录到 errors 列表。
    """
    if obj_type == "doc":
        r = requests.get(
            f"{BASE}/doc/v2/{obj_token}/raw_content",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(
                f"飞书文档 {obj_token} 获取失败: code={data.get('code')} msg={data.get('msg')} "
                "(请确认应用已加入知识库成员，并开通云文档只读权限)"
            )
        return (data.get("data", {}).get("content") or "").strip()
    if obj_type == "docx":
        r = requests.get(
            f"{BASE}/docx/v1/documents/{obj_token}/raw_content",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise RuntimeError(
                f"飞书新版文档 {obj_token} 获取失败: code={data.get('code')} msg={data.get('msg')} "
                "(请确认应用已加入知识库成员，并开通「查看、评论和下载云空间中所有文件」权限)"
            )
        return (data.get("data", {}).get("content") or "").strip()
    raise RuntimeError(f"暂不支持的文档类型: {obj_type}")
