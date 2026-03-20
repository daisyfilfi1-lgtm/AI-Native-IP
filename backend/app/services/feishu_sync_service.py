"""
飞书知识库 → Memory（ip_assets）同步：按空间拉取节点与文档内容，做结构化分段后写入/更新。
"""
import hashlib
import os
import re
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.feishu_client import (
    get_doc_raw_content,
    get_tenant_access_token,
    list_nodes,
    list_spaces,
)
from app.services.vector_service import upsert_asset_vector

SECTION_MAX_CHARS = 1800
SECTION_OVERLAP = 120


def _collect_doc_nodes(
    token: str,
    space_id: str,
    parent_node_token: str | None = None,
    doc_types: tuple[str, ...] = ("doc", "docx"),
) -> list[dict]:
    """递归收集空间下所有类型为 doc/docx 的节点（扁平列表）。"""
    result: list[dict] = []
    for node in list_nodes(token, space_id, parent_node_token):
        obj_type = (node.get("obj_type") or "").lower()
        if obj_type in doc_types:
            result.append(node)
        if node.get("has_child"):
            result.extend(
                _collect_doc_nodes(
                    token,
                    space_id,
                    parent_node_token=node.get("node_token"),
                    doc_types=doc_types,
                )
            )
    return result


def _split_by_headings(content: str) -> list[tuple[str | None, str]]:
    """
    按 markdown 标题拆分文档，便于后续结构化检索。
    若无标题则回退固定长度分块。
    """
    text = (content or "").strip()
    if not text:
        return [(None, "")]

    heading_re = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
    chunks: list[tuple[str | None, str]] = []
    cur_title: str | None = None
    cur_lines: list[str] = []

    def flush() -> None:
        if not cur_lines:
            return
        body = "\n".join(cur_lines).strip()
        if body:
            chunks.append((cur_title, body))

    for line in text.splitlines():
        m = heading_re.match(line)
        if m:
            flush()
            cur_title = m.group(2).strip()
            cur_lines = []
            continue
        cur_lines.append(line)
    flush()

    # 没有可用标题时按长度切块
    if not chunks:
        out: list[tuple[str | None, str]] = []
        start = 0
        while start < len(text):
            end = min(start + SECTION_MAX_CHARS, len(text))
            part = text[start:end].strip()
            if part:
                out.append((None, part))
            start = end - SECTION_OVERLAP
            if start >= len(text):
                break
        return out or [(None, text)]

    # 二次兜底：单块过长时再切分
    normalized: list[tuple[str | None, str]] = []
    for title, block in chunks:
        if len(block) <= SECTION_MAX_CHARS:
            normalized.append((title, block))
            continue
        start = 0
        while start < len(block):
            end = min(start + SECTION_MAX_CHARS, len(block))
            part = block[start:end].strip()
            if part:
                normalized.append((title, part))
            start = end - SECTION_OVERLAP
            if start >= len(block):
                break
    return normalized or [(None, text)]


def sync_feishu_space_to_ip(
    db: Session,
    ip_id: str,
    space_id: str | None = None,
    app_id: str | None = None,
    app_secret: str | None = None,
) -> dict[str, Any]:
    """
    将飞书知识库同步到指定 IP 的 Memory（ip_assets）。
    - 若未传 space_id，则同步第一个有权限的空间。
    - 使用环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET，或传入 app_id / app_secret。
    返回：{ "synced": 数量, "failed": 数量, "errors": [...] }
    """
    app_id = app_id or os.environ.get("FEISHU_APP_ID")
    app_secret = app_secret or os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        return {"synced": 0, "failed": 0, "errors": ["FEISHU_APP_ID / FEISHU_APP_SECRET 未配置"]}

    token = get_tenant_access_token(app_id, app_secret)

    if not space_id:
        spaces = list_spaces(token)
        if not spaces:
            return {"synced": 0, "failed": 0, "errors": ["未获取到任何知识空间，请确认应用已加入目标知识库成员"]}
        space_id = spaces[0].get("space_id")
        if not space_id:
            return {"synced": 0, "failed": 0, "errors": ["知识空间 ID 为空"]}

    nodes = _collect_doc_nodes(token, space_id)
    synced = 0
    failed = 0
    errors: list[str] = []

    for node in nodes:
        node_token = node.get("node_token")
        obj_token = node.get("obj_token")
        obj_type = (node.get("obj_type") or "").lower()
        title = (node.get("title") or "未命名").strip() or "未命名"
        if not obj_token or obj_type not in ("doc", "docx"):
            continue
        try:
            content = get_doc_raw_content(token, obj_type, obj_token)
        except Exception as e:
            failed += 1
            errors.append(f"{title}({obj_token}): {e}")
            continue

        sections = _split_by_headings(content or "")
        heading_titles = [x[0] for x in sections if x[0]]
        total_sections = max(1, len(sections))

        for idx, (section_title, section_content) in enumerate(sections):
            raw = f"{space_id}_{obj_token}_{idx}"
            asset_id = "feishu_" + hashlib.sha256(raw.encode()).hexdigest()[:32]
            existing = db.query(IPAsset).filter(IPAsset.asset_id == asset_id).first()

            meta = {
                "source": "feishu_kb",
                "feishu_space_id": space_id,
                "feishu_node_token": node_token,
                "feishu_obj_token": obj_token,
                "feishu_obj_type": obj_type,
                "doc_title": title,
                "section_title": section_title,
                "chunk_index": idx,
                "total_chunks": total_sections,
                "outline": heading_titles[:30],
            }
            final_title = title if not section_title else f"{title} / {section_title}"
            final_content = section_content or "(无文本)"

            if existing:
                existing.title = final_title
                existing.content = final_content
                base_meta = existing.asset_meta if existing.asset_meta else {}
                existing.asset_meta = {**base_meta, **meta}
                db.flush()
                try:
                    upsert_asset_vector(
                        db,
                        asset_id=existing.asset_id,
                        ip_id=ip_id,
                        content=existing.content or "",
                    )
                except Exception:
                    pass
            else:
                db.add(
                    IPAsset(
                        asset_id=asset_id,
                        ip_id=ip_id,
                        asset_type="data",
                        title=final_title,
                        content=final_content,
                        content_vector_ref=None,
                        asset_meta=meta,
                        relations=[],
                        status="active",
                    )
                )
                db.flush()
                try:
                    upsert_asset_vector(
                        db,
                        asset_id=asset_id,
                        ip_id=ip_id,
                        content=final_content,
                    )
                except Exception:
                    pass
            synced += 1

    db.commit()
    return {"synced": synced, "failed": failed, "errors": errors[:20]}
