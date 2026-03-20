"""
百度网盘 Open API 凭证：access_token 存 integration_config，或环境变量 BAIDU_PAN_ACCESS_TOKEN。
"""
import os

from sqlalchemy.orm import Session

from app.db.models import IntegrationConfig

BAIDU_KEY = "baidu_netdisk"


def get_baidu_access_token(db: Session) -> str | None:
    """优先读管理后台配置的 access_token，否则读环境变量。"""
    row = (
        db.query(IntegrationConfig)
        .filter(IntegrationConfig.key == BAIDU_KEY)
        .first()
    )
    if row and isinstance(row.value_json, dict):
        tok = (row.value_json.get("access_token") or "").strip()
        if tok:
            return tok
    env_tok = (os.environ.get("BAIDU_PAN_ACCESS_TOKEN") or "").strip()
    return env_tok or None


def get_baidu_config_display(db: Session) -> dict:
    """供管理后台展示：返回完整 access_token 便于编辑（与飞书 app_id 一致策略）。"""
    row = (
        db.query(IntegrationConfig)
        .filter(IntegrationConfig.key == BAIDU_KEY)
        .first()
    )
    if row and isinstance(row.value_json, dict):
        v = row.value_json
        token = (v.get("access_token") or "").strip()
        app_key = (v.get("app_key") or "").strip()
        return {
            "configured": bool(token),
            "access_token": token,
            "has_access_token": bool(token),
            "app_key": app_key,
        }
    env_tok = (os.environ.get("BAIDU_PAN_ACCESS_TOKEN") or "").strip()
    return {
        "configured": bool(env_tok),
        "access_token": env_tok,
        "has_access_token": bool(env_tok),
        "app_key": "",
    }


def set_baidu_config(db: Session, access_token: str, app_key: str | None = None) -> None:
    """保存百度网盘 access_token（及可选 app_key）。"""
    row = (
        db.query(IntegrationConfig)
        .filter(IntegrationConfig.key == BAIDU_KEY)
        .first()
    )
    value: dict = {"access_token": access_token.strip()}
    if app_key is not None and str(app_key).strip():
        value["app_key"] = str(app_key).strip()
    if row:
        if isinstance(row.value_json, dict):
            merged = {**row.value_json, **value}
        else:
            merged = value
        row.value_json = merged
        db.flush()
    else:
        db.add(IntegrationConfig(key=BAIDU_KEY, value_json=value))
        db.flush()
    db.commit()
