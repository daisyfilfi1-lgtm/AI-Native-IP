"""
飞书知识库 → Memory（ip_assets）同步：按空间拉取节点与文档内容并写入/更新 ip_assets。
"""
import hashlib
import os
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.feishu_client import (
    get_doc_raw_content,
    get_tenant_access_token,
    list_nodes,
    list_spaces,
)


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

        # 稳定且唯一的 asset_id（≤64 字符），便于后续增量更新
        raw = f"{space_id}_{obj_token}"
        asset_id = "feishu_" + hashlib.sha256(raw.encode()).hexdigest()[:32]
        existing = db.query(IPAsset).filter(IPAsset.asset_id == asset_id).first()
        meta = {
            "source": "feishu_kb",
            "feishu_space_id": space_id,
            "feishu_node_token": node_token,
            "feishu_obj_token": obj_token,
            "feishu_obj_type": obj_type,
        }
        if existing:
            existing.title = title
            existing.content = content or "(无文本)"
            existing.asset_meta = {**existing.asset_meta or {}, **meta}
            db.flush()
        else:
            db.add(
                IPAsset(
                    asset_id=asset_id,
                    ip_id=ip_id,
                    asset_type="data",
                    title=title,
                    content=content or "(无文本)",
                    content_vector_ref=None,
                    asset_meta=meta,
                    relations=[],
                    status="active",
                )
            )
            db.flush()
        synced += 1

    db.commit()
    return {"synced": synced, "failed": failed, "errors": errors[:20]}
