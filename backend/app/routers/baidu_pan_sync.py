"""
百度网盘同步：管理后台保存 access_token、触发同步到 IP Memory。
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.baidu_pan_config_service import (
    get_baidu_access_token,
    get_baidu_config_display,
    set_baidu_config,
)
from app.services.baidu_pan_sync_service import sync_baidu_netdisk_to_ip
from app.services.memory_config_service import get_ip

router = APIRouter()


class BaiduConfigResponse(BaseModel):
    configured: bool
    access_token: str
    has_access_token: bool
    app_key: str


class BaiduConfigSaveRequest(BaseModel):
    access_token: str = Field(..., min_length=1, description="百度网盘 Open API access_token")
    app_key: str | None = Field(None, description="可选，开放平台 AppKey（仅备忘）")


class SyncBaiduRequest(BaseModel):
    ip_id: str = Field(..., description="同步到该 IP 的 Memory")
    remote_path: str = Field(
        "/",
        description="网盘目录，如 / 或 /我的资源/笔记",
    )
    recursive: bool = Field(True, description="是否递归子目录（有单次同步文件数上限）")


class SyncBaiduResponse(BaseModel):
    synced: int
    failed: int
    errors: list[str]


@router.get("/integrations/baidu/config", response_model=BaiduConfigResponse)
def get_baidu_config(db: Session = Depends(get_db)) -> Any:
    """获取百度网盘配置（access_token 明文便于再次编辑）。"""
    d = get_baidu_config_display(db)
    return BaiduConfigResponse(**d)


@router.post("/integrations/baidu/config")
def save_baidu_config(
    payload: BaiduConfigSaveRequest,
    db: Session = Depends(get_db),
) -> Any:
    """保存百度网盘 access_token。"""
    set_baidu_config(db, payload.access_token, app_key=payload.app_key)
    return {"success": True}


@router.post("/integrations/baidu/sync", response_model=SyncBaiduResponse)
def sync_baidu(request: SyncBaiduRequest, db: Session = Depends(get_db)) -> Any:
    """将百度网盘目录下的文本文件同步到指定 IP 的 Memory。"""
    if not get_ip(db, request.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {request.ip_id}")
    token = get_baidu_access_token(db)
    if not token:
        raise HTTPException(
            status_code=503,
            detail="请先在「百度网盘」中填写 access_token，或配置环境变量 BAIDU_PAN_ACCESS_TOKEN",
        )
    result = sync_baidu_netdisk_to_ip(
        db,
        ip_id=request.ip_id,
        access_token=token,
        remote_path=request.remote_path,
        recursive=request.recursive,
    )
    if result.get("errors") and result.get("synced") == 0 and result.get("failed") == 0:
        raise HTTPException(status_code=400, detail=result["errors"][0] if result["errors"] else "同步失败")
    return result
