"""
飞书知识库同步服务 - 增量同步版本
实现文档级别的变更检测，只同步新增/更新的内容
"""
import hashlib
import os
import re
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.feishu_client import (
    get_doc_raw_content,
    get_tenant_access_token,
    list_nodes,
    list_spaces,
)
from app.services.vector_service_qdrant import upsert_asset_vector, delete_asset_vector

SECTION_MAX_CHARS = 1800
SECTION_OVERLAP = 120


class FeishuSyncState:
    """飞书同步状态跟踪"""
    
    def __init__(self, db: Session, ip_id: str, space_id: str):
        self.db = db
        self.ip_id = ip_id
        self.space_id = space_id
    
    def get_sync_marker(self) -> Optional[datetime]:
        """获取上次同步时间"""
        from app.db.models import IntegrationConfig
        
        key = f"feishu_sync_{self.ip_id}_{self.space_id}"
        row = self.db.query(IntegrationConfig).filter(
            IntegrationConfig.key == key
        ).first()
        
        if row and row.value_json:
            ts = row.value_json.get("last_sync_at")
            if ts:
                return datetime.fromisoformat(ts)
        return None
    
    def update_sync_marker(self, sync_time: datetime):
        """更新同步时间"""
        from app.db.models import IntegrationConfig
        
        key = f"feishu_sync_{self.ip_id}_{self.space_id}"
        row = self.db.query(IntegrationConfig).filter(
            IntegrationConfig.key == key
        ).first()
        
        if row:
            row.value_json = {
                "last_sync_at": sync_time.isoformat(),
                "doc_count": 0,
            }
        else:
            row = IntegrationConfig(
                key=key,
                value_json={
                    "last_sync_at": sync_time.isoformat(),
                    "doc_count": 0,
                }
            )
            self.db.add(row)
        self.db.commit()
    
    def get_doc_content_hash(self, obj_token: str) -> Optional[str]:
        """获取本地存储的文档内容hash"""
        # 查找该IP下来自该space的任意一个asset
        assets = self.db.query(IPAsset).filter(
            IPAsset.ip_id == self.ip_id,
            IPAsset.asset_meta["feishu_space_id"] == self.space_id,
            IPAsset.asset_meta["feishu_obj_token"] == obj_token,
        ).limit(1).all()
        
        if assets:
            return assets[0].asset_meta.get("content_hash")
        return None


def _compute_content_hash(content: str) -> str:
    """计算内容hash用于变更检测"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _collect_doc_nodes(
    token: str,
    space_id: str,
    parent_node_token: str | None = None,
    doc_types: tuple[str, ...] = ("doc", "docx"),
) -> list[dict]:
    """递归收集空间下所有类型为 doc/docx 的节点"""
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


def sync_feishu_space_to_ip_incremental(
    db: Session,
    ip_id: str,
    space_id: str | None = None,
    app_id: str | None = None,
    app_secret: str | None = None,
    incremental: bool = True,
) -> dict[str, Any]:
    """
    将飞书知识库同步到指定 IP 的 Memory（ip_assets）- 支持增量同步
    
    参数:
        db: 数据库会话
        ip_id: IP ID
        space_id: 飞书空间ID（可选）
        app_id: 飞书应用ID（可选）
        app_secret: 飞书应用密钥（可选）
        incremental: 是否增量同步（默认True）
    
    返回: {
        "synced": 新增/更新的文档数,
        "skipped": 跳过的文档数（未变化）,
        "deleted": 删除的文档数,
        "errors": 错误列表
    }
    """
    app_id = app_id or os.environ.get("FEISHU_APP_ID")
    app_secret = app_secret or os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        return {"synced": 0, "skipped": 0, "deleted": 0, "errors": ["FEISHU_APP_ID / FEISHU_APP_SECRET 未配置"]}

    token = get_tenant_access_token(app_id, app_secret)

    if not space_id:
        spaces = list_spaces(token)
        if not spaces:
            return {"synced": 0, "skipped": 0, "deleted": 0, "errors": ["未获取到任何知识空间"]}
        space_id = spaces[0].get("space_id")
        if not space_id:
            return {"synced": 0, "skipped": 0, "deleted": 0, "errors": ["知识空间 ID 为空"]}

    # 初始化同步状态跟踪器
    sync_state = FeishuSyncState(db, ip_id, space_id)
    
    # 获取远程文档列表
    remote_nodes = _collect_doc_nodes(token, space_id)
    
    # 构建远程文档映射
    remote_doc_map: dict[str, dict] = {}
    for node in remote_nodes:
        obj_token = node.get("obj_token")
        if obj_token:
            remote_doc_map[obj_token] = node
    
    # 获取本地已有文档
    local_assets = db.query(IPAsset).filter(
        IPAsset.ip_id == ip_id,
        IPAsset.asset_meta["feishu_space_id"] == space_id,
    ).all()
    
    local_doc_tokens = set()
    local_asset_map: dict[str, IPAsset] = {}
    
    for asset in local_assets:
        obj_token = asset.asset_meta.get("feishu_obj_token")
        if obj_token:
            local_doc_tokens.add(obj_token)
            local_asset_map[obj_token] = asset
    
    # 找出需要同步的文档
    remote_tokens = set(remote_doc_map.keys())
    new_or_updated_tokens = set()
    unchanged_tokens = set()
    
    if incremental:
        for obj_token in remote_tokens:
            node = remote_doc_map[obj_token]
            obj_type = (node.get("obj_type") or "").lower()
            title = (node.get("title") or "未命名").strip() or "未命名"
            
            try:
                content = get_doc_raw_content(token, obj_type, obj_token)
                content_hash = _compute_content_hash(content or "")
                
                # 检查本地是否有该文档
                local_asset = local_asset_map.get(obj_token)
                if local_asset:
                    local_hash = local_asset.asset_meta.get("content_hash")
                    if local_hash == content_hash:
                        # 内容未变化，跳过
                        unchanged_tokens.add(obj_token)
                        continue
                
                new_or_updated_tokens.add(obj_token)
            except Exception as e:
                # 获取内容失败，标记为需要同步
                new_or_updated_tokens.add(obj_token)
    else:
        # 全量同步模式
        new_or_updated_tokens = remote_tokens
    
    # 找出已删除的文档（远程不存在但本地存在）
    deleted_tokens = local_doc_tokens - remote_tokens
    
    synced = 0
    skipped = 0
    deleted = 0
    errors: list[str] = []

    # 1. 处理新增/更新的文档
    for obj_token in new_or_updated_tokens:
        node = remote_doc_map.get(obj_token)
        if not node:
            continue
            
        node_token = node.get("node_token")
        obj_type = (node.get("obj_type") or "").lower()
        title = (node.get("title") or "未命名").strip() or "未命名"
        
        if not obj_token or obj_type not in ("doc", "docx"):
            continue
        
        try:
            content = get_doc_raw_content(token, obj_type, obj_token)
            content_hash = _compute_content_hash(content or "")
        except Exception as e:
            errors.append(f"{title}({obj_token}): 获取内容失败 - {e}")
            continue

        sections = _split_by_headings(content or "")
        heading_titles = [x[0] for x in sections if x[0]]
        total_sections = max(1, len(sections))

        # 删除旧的asset（如果存在）
        existing_assets = db.query(IPAsset).filter(
            IPAsset.ip_id == ip_id,
            IPAsset.asset_meta["feishu_space_id"] == space_id,
            IPAsset.asset_meta["feishu_obj_token"] == obj_token,
        ).all()
        
        for old_asset in existing_assets:
            # 删除旧的向量
            try:
                delete_asset_vector(db, asset_id=old_asset.asset_id, ip_id=ip_id)
            except Exception:
                pass
            db.delete(old_asset)
        
        db.flush()

        # 写入新的asset
        for idx, (section_title, section_content) in enumerate(sections):
            raw = f"{space_id}_{obj_token}_{idx}"
            asset_id = "feishu_" + hashlib.sha256(raw.encode()).hexdigest()[:32]

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
                "content_hash": content_hash,
                "synced_at": datetime.utcnow().isoformat(),
            }
            final_title = title if not section_title else f"{title} / {section_title}"
            final_content = section_content or "(无文本)"

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
            
            # 写入Qdrant向量
            try:
                upsert_asset_vector(
                    db,
                    asset_id=asset_id,
                    ip_id=ip_id,
                    content=final_content,
                    metadata=meta,
                )
            except Exception:
                pass
            
            synced += 1

    # 2. 处理未变化的文档（跳过）
    skipped = len(unchanged_tokens)
    
    # 3. 处理已删除的文档
    for obj_token in deleted_tokens:
        assets_to_delete = db.query(IPAsset).filter(
            IPAsset.ip_id == ip_id,
            IPAsset.asset_meta["feishu_space_id"] == space_id,
            IPAsset.asset_meta["feishu_obj_token"] == obj_token,
        ).all()
        
        for asset in assets_to_delete:
            try:
                delete_asset_vector(db, asset_id=asset.asset_id, ip_id=ip_id)
            except Exception:
                pass
            db.delete(asset)
            deleted += 1

    db.commit()
    
    # 更新同步时间戳
    sync_state.update_sync_marker(datetime.utcnow())

    return {
        "synced": synced,
        "skipped": skipped,
        "deleted": deleted,
        "total_remote": len(remote_tokens),
        "total_local": len(local_doc_tokens),
        "errors": errors[:20]
    }


# 兼容旧接口
def sync_feishu_space_to_ip(
    db: Session,
    ip_id: str,
    space_id: str | None = None,
    app_id: str | None = None,
    app_secret: str | None = None,
) -> dict[str, Any]:
    """旧接口 - 全量同步"""
    return sync_feishu_space_to_ip_incremental(
        db, ip_id, space_id, app_id, app_secret, incremental=False
    )
