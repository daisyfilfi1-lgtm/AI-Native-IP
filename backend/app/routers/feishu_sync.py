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
from app.services.feishu_sync_service import sync_feishu_space_to_ip
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


class SyncFeishuResponse(BaseModel):
    synced: int
    failed: int
    errors: list[str]


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
    result = sync_feishu_space_to_ip(
        db,
        ip_id=request.ip_id,
        space_id=request.space_id,
        app_id=app_id,
        app_secret=app_secret,
    )
    if result.get("errors") and result.get("synced") == 0 and result.get("failed") == 0:
        raise HTTPException(status_code=400, detail=result["errors"][0] if result["errors"] else "同步失败")
    return result
