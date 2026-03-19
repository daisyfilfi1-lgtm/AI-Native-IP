"""
飞书凭证的读写：优先使用管理后台保存的配置，否则回退到环境变量。
"""
import os
from typing import Tuple

from sqlalchemy.orm import Session

from app.db.models import IntegrationConfig

FEISHU_KEY = "feishu"


def get_feishu_credentials(db: Session) -> Tuple[str | None, str | None]:
    """
    返回 (app_id, app_secret)。优先读 integration_config 表，若无则读环境变量。
    """
    row = db.query(IntegrationConfig).filter(IntegrationConfig.key == FEISHU_KEY).first()
    if row and isinstance(row.value_json, dict):
        app_id = row.value_json.get("app_id")
        app_secret = row.value_json.get("app_secret")
        if app_id and app_secret:
            return (app_id, app_secret)
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    return (app_id or None, app_secret or None)


def get_feishu_config_display(db: Session) -> dict:
    """供前端展示：是否已配置、app_id 脱敏，不返回 secret。"""
    row = db.query(IntegrationConfig).filter(IntegrationConfig.key == FEISHU_KEY).first()
    if row and isinstance(row.value_json, dict):
        app_id = row.value_json.get("app_id") or ""
        return {
            "configured": True,
            "app_id": app_id[:8] + "***" if len(app_id) > 8 else "***",
            "has_secret": bool(row.value_json.get("app_secret")),
        }
    env_id = os.environ.get("FEISHU_APP_ID")
    return {
        "configured": bool(env_id),
        "app_id": (env_id[:8] + "***") if env_id and len(env_id) > 8 else "***",
        "has_secret": bool(os.environ.get("FEISHU_APP_SECRET")),
    }


def set_feishu_config(db: Session, app_id: str, app_secret: str) -> None:
    """保存飞书凭证到 integration_config（key=feishu）。"""
    row = db.query(IntegrationConfig).filter(IntegrationConfig.key == FEISHU_KEY).first()
    value = {"app_id": app_id.strip(), "app_secret": app_secret.strip()}
    if row:
        row.value_json = value
        db.flush()
    else:
        db.add(IntegrationConfig(key=FEISHU_KEY, value_json=value))
        db.flush()
    db.commit()
