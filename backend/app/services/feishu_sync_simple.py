"""
极简飞书同步 - 只同步文本，不做向量
"""
import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.feishu_client import (
    get_tenant_access_token,
    get_doc_raw_content,
)
from app.services.feishu_sync_service_incremental import _collect_doc_nodes


def simple_sync(db: Session, ip_id: str, space_id: str, app_id: str, app_secret: str):
    """极简同步：只获取文档内容存入数据库"""
    
    token = get_tenant_access_token(app_id, app_secret)
    
    # 递归获取所有文档（包括子文件夹）
    nodes = _collect_doc_nodes(token, space_id)
    
    synced = 0
    errors = []
    
    for node in nodes:
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
        "total_remote": len(nodes),
        "errors": errors,
    }
