"""
飞书文档批量同步 - 根据提供的链接列表同步
"""
import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.feishu_client import (
    get_tenant_access_token,
)

BASE = "https://open.feishu.cn/open-apis"


def get_doc_raw_content_simple(token: str, obj_token: str) -> str:
    """获取文档纯文本"""
    import requests
    r = requests.get(
        f"{BASE}/docx/v1/documents/{obj_token}/raw_content",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 0:
        return f"[获取失败: code={data.get('code')} msg={data.get('msg')}]"
    return (data.get("data", {}).get("content") or "").strip()


# 用户提供的文档链接列表
DOC_LINKS = [
    {"name": "IP定位", "token": "IYW8wITd0iwhDKkhyL7cNuc8nIh"},
    {"name": "2026内容2.0升级规划", "token": "AyzNwF2wdi0E87k7dWYcIKn1nzf"},
    {"name": "核心方法论和反常识逻辑库", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "专属语感与口癖词典", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "十年自述", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "个人高光与低谷素材库", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "爆火文案", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "过往爆款分析与总结", "token": "EOotwUo2QiJMrFkH5x9cKTzDnle"},
    {"name": "私房创业班", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "私房营养早餐计划", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "学员案例库(00后)", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "学员案例库(40岁面包哥)", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "学员案例库(58岁幼儿园园长)", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "学员案例库(传统早餐老板转型)", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "学员案例库(昆明三姐妹)", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "学员案例库(宝妈)", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "学员案例库(三娃宝妈逆袭)", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "学员案例库(私房同行加品)", "token": "FHNJwOs5Ki5rjBkn0W9cVwqlnDh"},
    {"name": "客户分层画像", "token": "Txruw6Nu2icT3vkgXQRc7PElnLg"},
    {"name": "销售转化的卖点梳理", "token": "RJvRwu9wLir3d7kYotrcRSVZnvg"},
    {"name": "竞品分析", "token": "RuAkwFAZwiOYZqkDOJ6cSoBsnvc"},
]


def sync_by_links(db: Session, ip_id: str, app_id: str, app_secret: str):
    """根据链接列表同步文档"""
    
    token = get_tenant_access_token(app_id, app_secret)
    
    synced = 0
    errors = []
    seen_tokens = set()
    
    for doc in DOC_LINKS:
        token_value = doc["token"]
        title = doc["name"]
        
        # 去重
        if token_value in seen_tokens:
            continue
        seen_tokens.add(token_value)
        
        try:
            content = get_doc_raw_content_simple(token, token_value)
            
            # 检查是否获取失败
            if "获取失败" in content:
                errors.append(f"{title}: {content}")
                continue
            
            if not content:
                errors.append(f"{title}: 无内容")
                continue
            
            # 生成 asset_id
            raw = f"link_{token_value}"
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
                        "source": "feishu_link",
                        "feishu_obj_token": token_value,
                        "feishu_obj_type": "docx",
                    },
                    relations=[],
                    status="active",
                )
                db.add(asset)
            
            synced += 1
            db.commit()
            
        except Exception as e:
            errors.append(f"{title}: {str(e)[:80]}")
    
    return {
        "synced": synced,
        "total": len(DOC_LINKS),
        "unique": len(seen_tokens),
        "errors": errors,
    }
