"""
百度网盘 Open API（xpan）轻量封装：列目录、下载文件内容。
文档：https://pan.baidu.com/union/doc/
"""
from __future__ import annotations

import json
from typing import Any

import requests

XPAN_FILE_BASE = "https://pan.baidu.com/rest/2.0/xpan/file"
_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Native-IP-Factory/1.0)",
}


def _parse_json_or_raise(resp: requests.Response) -> dict[str, Any]:
    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        raise RuntimeError(f"非 JSON 响应: HTTP {resp.status_code}") from e
    err = data.get("errno")
    if err not in (0, None, "0"):
        msg = data.get("errmsg") or data.get("show_msg") or str(err)
        raise RuntimeError(msg)
    return data


def list_dir(
    access_token: str,
    remote_path: str = "/",
    *,
    start: int = 0,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """列出指定目录下一层文件/子目录。"""
    params = {
        "method": "list",
        "dir": remote_path.rstrip("/") or "/",
        "start": start,
        "limit": limit,
        "access_token": access_token,
    }
    r = requests.get(XPAN_FILE_BASE, params=params, timeout=60, headers=_DEFAULT_HEADERS)
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").lower()
    if "application/json" not in ctype:
        raise RuntimeError(f"列目录失败: 非 JSON 响应 ({ctype})")
    data = _parse_json_or_raise(r)
    return list(data.get("list") or [])


def download_file_bytes(access_token: str, remote_file_path: str) -> bytes:
    """
    下载网盘文件内容（小文件）。
    大文件建议使用分片下载；此处用于同步 txt/md 等小文本。
    """
    params = {
        "method": "download",
        "path": remote_file_path,
        "access_token": access_token,
    }
    r = requests.get(
        XPAN_FILE_BASE,
        params=params,
        timeout=120,
        allow_redirects=True,
        headers=_DEFAULT_HEADERS,
    )
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").lower()
    if "application/json" in ctype:
        data = _parse_json_or_raise(r)
        # 部分情况下返回 dlink
        dlink = data.get("dlink")
        if dlink:
            r2 = requests.get(
                dlink,
                params={"access_token": access_token},
                timeout=120,
                allow_redirects=True,
                headers=_DEFAULT_HEADERS,
            )
            r2.raise_for_status()
            return r2.content
        raise RuntimeError(data.get("errmsg") or "下载失败")
    return r.content


def is_dir(item: dict[str, Any]) -> bool:
    v = item.get("isdir")
    return v in (1, "1", True)
