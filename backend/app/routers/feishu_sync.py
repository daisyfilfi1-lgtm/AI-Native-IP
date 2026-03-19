"""
飞书知识库同步：列出空间、触发同步到指定 IP 的 Memory。
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.feishu_client import get_tenant_access_token, list_spaces
from app.services.feishu_sync_service import sync_feishu_space_to_ip
from app.services.memory_config_service import get_ip

router = APIRouter()


class SyncFeishuRequest(BaseModel):
    ip_id: str = Field(..., description="同步到该 IP 的 Memory")
    space_id: str | None = Field(None, description="飞书知识空间 ID，不传则用第一个有权限的空间")


class SyncFeishuResponse(BaseModel):
    synced: int
    failed: int
    errors: list[str]


@router.get("/integrations/feishu/spaces")
def list_feishu_spaces() -> Any:
    """
    列出当前应用有权限的飞书知识空间（用于选择要同步的 space_id）。
    需配置 FEISHU_APP_ID、FEISHU_APP_SECRET。
    """
    import os
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=503,
            detail="未配置 FEISHU_APP_ID / FEISHU_APP_SECRET，请在环境变量中配置",
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
    将飞书知识库同步到指定 IP 的 Memory（ip_assets）。
    会拉取空间内所有 doc/docx 节点内容并写入或更新素材。
    """
    if not get_ip(db, request.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {request.ip_id}")
    result = sync_feishu_space_to_ip(
        db,
        ip_id=request.ip_id,
        space_id=request.space_id,
    )
    if result.get("errors") and result.get("synced") == 0 and result.get("failed") == 0:
        raise HTTPException(status_code=400, detail=result["errors"][0] if result["errors"] else "同步失败")
    return result
