"""
极简飞书同步 - 只同步文本，不做向量
支持跟随链接
"""
import hashlib
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.feishu_client import (
    get_tenant_access_token,
    get_doc_raw_content,
)
from app.services.feishu_sync_service_incremental import _collect_doc_nodes


def extract_links(content: str) -> list[str]:
    """提取飞书文档链接"""
    # 飞书文档链接格式: https://xx.feishu.cn/doc/xxx 或 https://xx.feishu.cn/docs/xxx
    patterns = [
        r'https://[\w.-]+\.feishu\.cn/doc/[A-Za-z0-9]+',
        r'https://[\w.-]+\.feishu\.cn/docs/[A-Za-z0-9]+',
    ]
    
    links = []
    for pattern in patterns:
        matches = re.findall(pattern, content)
        links.extend(matches)
    
    return list(set(links))


def extract_doc_token(link: str) -> str | None:
    """从链接提取文档token"""
    # https://xxx.feishu.cn/doc/xxxx -> xxxx
    # https://xxx.feishu.cn/docs/xxxx -> xxxx
    match = re.search(r'/doc/([A-Za-z0-9]+)', link)
    if match:
        return match.group(1)
    match = re.search(r'/docs/([A-Za-z0-9]+)', link)
    if match:
        return match.group(1)
    return None


def simple_sync(db: Session, ip_id: str, space_id: str, app_id: str, app_secret: str, follow_links: bool = True):
    """极简同步：只获取文档内容存入数据库
    
    Args:
        follow_links: 是否跟随链接同步
    """
    
    token = get_tenant_access_token(app_id, app_secret)
    
    # 递归获取所有文档（包括子文件夹）
    nodes = _collect_doc_nodes(token, space_id)
    
    synced = 0
    errors = []
    all_docs = {}  # token -> {title, content}
    
    # 第一轮：获取所有主文档
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
            
            all_docs[obj_token] = {
                "title": title,
                "content": content,
                "obj_type": obj_type,
            }
            
        except Exception as e:
            errors.append(f"{title}: {str(e)[:50]}")
    
    # 第二轮：跟随链接（如果启用）
    if follow_links:
        linked_tokens = set()
        for token_key, doc in all_docs.items():
            links = extract_links(doc["content"])
            for link in links:
                linked_token = extract_doc_token(link)
                if linked_token and linked_token not in all_docs and linked_token not in linked_tokens:
                    linked_tokens.add(linked_token)
        
        # 获取链接指向的文档
        for linked_token in linked_tokens:
            try:
                content = get_doc_raw_content(token, "docx", linked_token)
                if content and "获取失败" not in content:
                    all_docs[linked_token] = {
                        "title": f"[链接] {linked_token[:8]}",
                        "content": content,
                        "obj_type": "docx",
                    }
            except Exception as e:
                errors.append(f"链接文档 {linked_token[:8]}: {str(e)[:30]}")
    
    # 第三轮：存入数据库
    for obj_token, doc in all_docs.items():
        title = doc["title"]
        content = doc["content"]
        
        try:
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
                        "feishu_obj_type": doc["obj_type"],
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
        "linked_docs": len(all_docs) - len(nodes),
        "errors": errors,
    }
