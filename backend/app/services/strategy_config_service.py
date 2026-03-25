"""
策略 Agent 配置：四维权重、选题评分卡滑块、拍摄阈值、黑名单、抓取参数。
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.db.models import IP

DEFAULT_STRATEGY_CONFIG: Dict[str, Any] = {
    "four_dim_weights": {
        "traffic": 30,
        "monetization": 30,
        "fit": 25,
        "cost": 15,
    },
    "scorecard_sliders": {
        "target": 2,
        "pain": 2,
        "viral": 2,
        "cost": 0,
        "monetization": 2,
    },
    "shoot_threshold": 7,
    "topic_blacklist": [],
    "crawl": {
        "frequency": "1hour",
        "viral_like_threshold": 10000,
        "auto_crawl": True,
    },
}

_SCORECARD_LIMITS = {
    "target": (0, 2),
    "pain": (0, 2),
    "viral": (0, 3),
    "cost": (-1, 1),
    "monetization": (0, 2),
}


def _clamp_int(v: Any, lo: int, hi: int) -> int:
    try:
        x = int(round(float(v)))
    except (TypeError, ValueError):
        x = lo
    return max(lo, min(hi, x))


def normalize_four_dim_weights(raw: Optional[Dict[str, Any]]) -> Dict[str, int]:
    keys = ("traffic", "monetization", "fit", "cost")
    if not isinstance(raw, dict):
        raw = {}
    vals = [_clamp_int(raw.get(k, DEFAULT_STRATEGY_CONFIG["four_dim_weights"][k]), 0, 100) for k in keys]
    s = sum(vals)
    if s == 0:
        return {k: DEFAULT_STRATEGY_CONFIG["four_dim_weights"][k] for k in keys}
    # 按比例缩放到总和为 100，最后一条用差额修正
    scaled = [max(0, min(100, round(v * 100 / s))) for v in vals]
    diff = 100 - sum(scaled)
    scaled[-1] = max(0, min(100, scaled[-1] + diff))
    return dict(zip(keys, scaled))


def normalize_scorecard_sliders(raw: Optional[Dict[str, Any]]) -> Dict[str, int]:
    if not isinstance(raw, dict):
        raw = {}
    out: Dict[str, int] = {}
    for k, (lo, hi) in _SCORECARD_LIMITS.items():
        out[k] = _clamp_int(raw.get(k, DEFAULT_STRATEGY_CONFIG["scorecard_sliders"][k]), lo, hi)
    return out


def scorecard_total(sliders: Dict[str, int]) -> int:
    return sum(int(sliders.get(k, 0)) for k in _SCORECARD_LIMITS)


def merge_strategy_config(saved: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = deepcopy(DEFAULT_STRATEGY_CONFIG)
    if not isinstance(saved, dict):
        return base
    if isinstance(saved.get("four_dim_weights"), dict):
        base["four_dim_weights"] = normalize_four_dim_weights(saved["four_dim_weights"])
    if isinstance(saved.get("scorecard_sliders"), dict):
        base["scorecard_sliders"] = normalize_scorecard_sliders(saved["scorecard_sliders"])
    if saved.get("shoot_threshold") is not None:
        base["shoot_threshold"] = _clamp_int(saved.get("shoot_threshold"), 0, 10)
    if isinstance(saved.get("topic_blacklist"), list):
        base["topic_blacklist"] = [str(x).strip() for x in saved["topic_blacklist"] if str(x).strip()][:200]
    crawl = saved.get("crawl")
    if isinstance(crawl, dict):
        freq = str(crawl.get("frequency", base["crawl"]["frequency"]))
        if freq not in ("15min", "1hour", "6hours", "daily"):
            freq = base["crawl"]["frequency"]
        base["crawl"] = {
            "frequency": freq,
            "viral_like_threshold": max(0, _clamp_int(crawl.get("viral_like_threshold"), 0, 999999999)),
            "auto_crawl": bool(crawl.get("auto_crawl", True)),
        }
    return base


def get_merged_config(db: Session, ip_id: str) -> dict:
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        return {}
    merged = merge_strategy_config(ip.strategy_config if isinstance(ip.strategy_config, dict) else None)
    merged["scorecard_total"] = scorecard_total(merged["scorecard_sliders"])
    merged["shoot_recommendation"] = (
        "可拍摄" if merged["scorecard_total"] >= merged["shoot_threshold"] else "待评估"
    )
    return merged
