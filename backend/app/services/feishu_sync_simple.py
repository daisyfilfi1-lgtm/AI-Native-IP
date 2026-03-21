"""
极简飞书同步 - 同步整个知识库所有文档
"""
import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.feishu_client import (
    get_tenant_access_token,
    list_nodes,
    get_doc_raw_content,
)


def simple_sync(db: Session, ip_id: str, space_id: str, app_id: str, app_secret: str):
    """同步整个知识库所有文档（包括文件夹内的）"""
    
    token = get_tenant_access_token(app_id, app_secret)
    
    # 递归获取所有节点
    def get_all_docs(space_id: str, parent_token: str = None) -> list:
        """递归获取所有文档"""
        docs = []
        nodes = list(list_nodes(token, space_id, parent_token))
        
        for node in nodes:
            obj_type = node.get("obj_type", "").lower()
            node_token = node.get("node_token")
            has_child = node.get("has_child", False)
            
            # 如果是文档类型
            if obj_type in ("doc", "docx"):
                docs.append(node)
            
            # 如果有子节点（文件夹），递归获取
            if has_child and node_token:
                docs.extend(get_all_docs(space_id, node_token))
        
        return docs
    
    # 获取所有文档
    all_nodes = get_all_docs(space_id)
    
    synced = 0
    errors = []
    
    for node in all_nodes:
        obj_token = node.get("obj_token")
        obj_type = (node.get("obj_type") or "").lower()
        title = (node.get("title") or "未命名").strip()
        
        if not obj_token or obj_type not in ("doc", "docx"):
            continue
        
        try:
            content = get_doc_raw_content(token, obj_type, obj_token)
            if not content or "获取失败" in content:
                errors.append(f"{title}: 获取内容失败")
                continue
            
            # 生成 asset_id
            raw = f"{space_id}_{obj_token}"
            asset_id = "feishu_" + hashlib.sha256(raw.encode()).hexdigest()[:32]
            
            # 检查是否已存在
            existing = db.query(IPAsset).filter(
                IPAsset.asset_id == asset_id
            ).first()
            
            if existing:
                existing.content = content
                existing.updated_at = datetime.utcnow()
            else:
                asset = IPAsset(
                    asset_id=asset_id,
                    ip_id=ip_id,
                    asset_type="data",
                    title=title,
                    content=content,
                    content_vector_ref=None,
                    asset_meta={
                        "source": "feishu_kb",
                        "feishu_space_id": space_id,
                        "feishu_obj_token": obj_token,
                        "feishu_obj_type": obj_type,
                    },
                    relations=[],
                    status="active",
                )
                db.add(asset)
            
            synced += 1
            db.commit()
            
        except Exception as e:
            errors.append(f"{title}: {str(e)[:50]}")
    
    return {
        "synced": synced,
        "total_found": len(all_nodes),
        "errors": errors[:10],  # 只返回前10个错误
    }
