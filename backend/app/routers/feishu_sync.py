"""
飞书知识库同步：管理后台保存凭证、列出空间、触发同步到 IP Memory。
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.feishu_client import get_tenant_access_token, list_spaces
from app.services.feishu_config_service import (
    get_feishu_config_display,
    get_feishu_credentials,
    set_feishu_config,
)
from app.services.feishu_sync_simple import simple_sync as sync_feishu_space_to_ip_incremental
from app.services.integration_binding_service import get_binding, upsert_binding
from app.services.memory_config_service import get_ip

router = APIRouter()


class FeishuConfigResponse(BaseModel):
    configured: bool
    app_id: str
    has_secret: bool


class FeishuConfigSaveRequest(BaseModel):
    app_id: str = Field(..., min_length=1)
    app_secret: str = Field(..., min_length=1)


class SyncFeishuRequest(BaseModel):
    ip_id: str = Field(..., description="同步到该 IP 的 Memory")
    space_id: str | None = Field(None, description="飞书知识空间 ID，不传则用第一个有权限的空间")
    incremental: bool = Field(True, description="增量同步（仅同步新增/更新的文档），默认开启")


class SyncFeishuResponse(BaseModel):
    synced: int = Field(..., description="新增/更新的片段数")
    skipped: int = Field(0, description="跳过的片段数（内容未变化）")
    deleted: int = Field(0, description="删除的片段数（远程已删除）")
    failed: int = Field(0, description="失败的片段数")
    total_remote: int = Field(0, description="远程文档总数")
    total_local: int = Field(0, description="本地已有文档数")
    errors: list[str] = Field(default_factory=list)
    used_space_id: str | None = None


class FeishuBindingSaveRequest(BaseModel):
    ip_id: str = Field(..., description="系统内 IP ID")
    space_id: str = Field(..., min_length=1, description="飞书知识空间 ID")
    space_name: str | None = Field(None, description="空间名称（可选，展示用）")


class FeishuBindingResponse(BaseModel):
    ip_id: str
    space_id: str
    space_name: str | None = None


@router.get("/integrations/feishu/config", response_model=FeishuConfigResponse)
def get_feishu_config(db: Session = Depends(get_db)) -> Any:
    """获取飞书配置状态（app_id 明文便于再次编辑；secret 不落库到响应）。"""
    d = get_feishu_config_display(db)
    return FeishuConfigResponse(**d)


@router.post("/integrations/feishu/config")
def save_feishu_config(
    payload: FeishuConfigSaveRequest,
    db: Session = Depends(get_db),
) -> Any:
    """管理后台保存飞书 App ID / App Secret，后续同步与列空间将优先使用此处配置。"""
    set_feishu_config(db, payload.app_id, payload.app_secret)
    return {"success": True}


@router.get("/integrations/feishu/spaces")
def list_feishu_spaces(db: Session = Depends(get_db)) -> Any:
    """
    列出当前应用有权限的飞书知识空间。凭证优先从管理后台已保存的配置读取，否则从环境变量读取。
    """
    app_id, app_secret = get_feishu_credentials(db)
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=503,
            detail="请先在「飞书应用凭证」中填写 App ID 和 App Secret，或配置环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET",
        )
    try:
        token = get_tenant_access_token(app_id, app_secret)
        spaces = list_spaces(token)
        return {"items": [{"space_id": s.get("space_id"), "name": s.get("name"), "description": s.get("description")} for s in spaces]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"飞书 API 调用失败: {e}") from e


@router.post("/integrations/feishu/sync", response_model=SyncFeishuResponse)
def sync_feishu(request: SyncFeishuRequest, db: Session = Depends(get_db)) -> Any:
    """
    将飞书知识库同步到指定 IP 的 Memory（ip_assets）。凭证优先使用管理后台已保存的配置。
    """
    if not get_ip(db, request.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {request.ip_id}")
    app_id, app_secret = get_feishu_credentials(db)
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=503,
            detail="请先在「飞书应用凭证」中填写 App ID 和 App Secret",
        )
    chosen_space_id = request.space_id
    if not chosen_space_id:
        bound = get_binding(db, "feishu", request.ip_id)
        if bound and bound.external_id:
            chosen_space_id = bound.external_id

    result = sync_feishu_space_to_ip_incremental(
        db,
        ip_id=request.ip_id,
        space_id=chosen_space_id,
        app_id=app_id,
        app_secret=app_secret,
    )
    used_space_id = chosen_space_id
    if result.get("errors") and result.get("synced", 0) == 0:
        raise HTTPException(
            status_code=502,
            detail=result["errors"][0] if result["errors"] else "飞书同步失败",
        )
    return {**result, "used_space_id": used_space_id}


@router.get("/integrations/feishu/test-fetch")
def test_fetch_docs(db: Session = Depends(get_db)) -> Any:
    """测试：获取所有文档包括子节点"""
    app_id, app_secret = get_feishu_credentials(db)
    if not app_id or not app_secret:
        return {"error": "no credentials"}
    
    try:
        import requests as req
        # 获取token
        r = req.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=10
        )
        data = r.json()
        if data.get("code") != 0:
            return {"error": "token failed", "detail": data}
        
        token = data.get("tenant_access_token")
        
        # 获取第一个文档的完整内容
        obj_token = "FDYQd3g9AoQMGnxtRBicBxibnKe"
        
        # 获取docx内容
        r2 = req.get(
            f"https://open.feishu.cn/open-apis/docx/v1/documents/{obj_token}/raw_content",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )
        
        content_data = r2.json()
        
        return {
            "doc_token": obj_token,
            "content": content_data.get("data", {}).get("content", "")[:2000],
            "has_content": bool(content_data.get("data", {}).get("content")),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/integrations/feishu/binding", response_model=FeishuBindingResponse | None)
def get_feishu_binding(ip_id: str, db: Session = Depends(get_db)) -> Any:
    """获取指定 IP 的飞书默认空间映射。"""
    row = get_binding(db, "feishu", ip_id)
    if not row:
        return None
    return FeishuBindingResponse(
        ip_id=row.ip_id,
        space_id=row.external_id,
        space_name=row.external_name,
    )


@router.post("/integrations/feishu/binding", response_model=FeishuBindingResponse)
def save_feishu_binding(
    payload: FeishuBindingSaveRequest,
    db: Session = Depends(get_db),
) -> Any:
    """保存飞书空间与 IP 的默认映射（用于后续同步自动选空间）。"""
    if not get_ip(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    row = upsert_binding(
        db,
        integration="feishu",
        ip_id=payload.ip_id,
        external_id=payload.space_id,
        external_name=payload.space_name,
        extra={},
    )
    return FeishuBindingResponse(
        ip_id=row.ip_id,
        space_id=row.external_id,
        space_name=row.external_name,
    )
