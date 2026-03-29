"""
Remix Agent API：动态配置管理
- 四大脚本模板
- 解构规则
- 原创度保障阈值
- 高级配置
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP, RemixAgentConfig

router = APIRouter()


# ----- 默认配置 -----

DEFAULT_SCRIPT_TEMPLATES = [
    {
        "id": "opinion",
        "name": "说观点",
        "emoji": "💡",
        "desc": "吸真粉/高互动",
        "enabled": True,
        "structure": [
            {"part": "钩子", "duration": "3秒", "desc": "争议性观点", "example": '"90%的人不知道，努力是职场最大的陷阱"'},
            {"part": "论据", "duration": "30秒", "desc": "3个维度证明（数据/案例/逻辑）", "example": "第一，数据显示...第二，真实案例...第三，逻辑推导..."},
            {"part": "升华", "duration": "5秒", "desc": "情感共鸣+引导互动", "example": '"你同意吗？评论区见"'},
        ],
        "keywords": ["我认为", "真相是", "揭秘", "说白了"],
        "bestFor": "建立专业人设，引发评论区讨论",
        "color": "from-yellow-500 to-amber-500",
        "bgColor": "bg-yellow-500/10",
        "borderColor": "border-yellow-500/20"
    },
    {
        "id": "process",
        "name": "晒过程",
        "emoji": "🎬",
        "desc": "强转化/近变现",
        "enabled": True,
        "structure": [
            {"part": "钩子", "duration": "3秒", "desc": "十大勾子技巧", "example": '"花5000元买的教训"'},
            {"part": "过程", "duration": "40秒", "desc": "服务/产品交付全过程", "example": "第一步...第二步...最关键的一步..."},
            {"part": "结果", "duration": "7秒", "desc": "成果展示+CTA", "example": '"这就是专业，需要同款服务私信我"'},
        ],
        "contentTypes": ["过程展示", "产品测评", "任务挑战", "事件体验"],
        "hookTechniques": ["反常识开头", "进度条预告", "身份悬念", "花X元买的教训"],
        "bestFor": "展示服务/产品交付过程，建立信任促成交",
        "color": "from-green-500 to-emerald-500",
        "bgColor": "bg-green-500/10",
        "borderColor": "border-green-500/20"
    },
    {
        "id": "knowledge",
        "name": "教知识",
        "emoji": "📚",
        "desc": "精准粉/高客单",
        "enabled": True,
        "structure": [
            {"part": "问题", "duration": "5秒", "desc": "具体问题或痛点", "example": '"Excel去重总是出错？"'},
            {"part": "方法", "duration": "35秒", "desc": "步骤详解", "example": "首先...然后...注意这个关键点..."},
            {"part": "总结", "duration": "5秒", "desc": "价值强化+引导", "example": '"学会了点个赞，想要更多技巧关注我"'},
        ],
        "topicMethods": ["解题型", "案例型", "推荐型", "揭秘型", "颠覆型"],
        "keywords": ["三步教你", "核心技巧", "必须知道", "干货"],
        "bestFor": "知识付费引流，筛选高意向用户",
        "color": "from-blue-500 to-cyan-500",
        "bgColor": "bg-blue-500/10",
        "borderColor": "border-blue-500/20"
    },
    {
        "id": "story",
        "name": "讲故事",
        "emoji": "📖",
        "desc": "立人设/高信任",
        "enabled": True,
        "structure": [
            {"part": "困境", "duration": "15秒", "desc": "建立共情", "example": '"2022年，我的公司现金流断裂..."'},
            {"part": "转折", "duration": "10秒", "desc": "点燃希望", "example": '"但一个数据让我改变了想法..."'},
            {"part": "方法", "duration": "20秒", "desc": "提供价值", "example": '"我做对了这三件事..."'},
            {"part": "结果", "duration": "5秒", "desc": "结果证明", "example": '"3年后，我还清了所有债务"'},
        ],
        "prototypes": ["小有成就型", "平凡英雄型", "重新成功型"],
        "emotionCurve": "困境(共情) → 转折(希望) → 方法(价值) → 结果(证明)",
        "bestFor": "高客单产品成交前，建立深度情感连接",
        "color": "from-purple-500 to-pink-500",
        "bgColor": "bg-purple-500/10",
        "borderColor": "border-purple-500/20"
    },
]

DEFAULT_DECONSTRUCT_RULES = {
    "script_template_recognition": {"enabled": True, "desc": "自动识别使用的四大模板类型"},
    "hook_pattern": {"enabled": True, "desc": "分析开头如何吸引注意力"},
    "emotion_curve": {"enabled": True, "desc": "识别情绪起伏的时间点"},
    "argument_structure": {"enabled": True, "desc": "提取逻辑框架和论据类型"},
    "visual_elements": {"enabled": False, "desc": "分析画面切换和特效使用"},
}

DEFAULT_ORIGINALITY_THRESHOLDS = {
    "text_repeat_rate": 25,  # 文本重复率阈值 %
    "structure_similarity": 40,  # 结构相似度阈值 %
}

DEFAULT_ADVANCED_SETTINGS = {
    "script_template_preference": "auto",  # auto/opinion/process/knowledge/story
    "hybrid_strategy": "best_of_breed",  # best_of_breed/single/hybrid
    "force_replace_rule": "all",  # all/partial/none
}


# ----- Pydantic 模型 -----

class ScriptTemplate(BaseModel):
    id: str
    name: str
    emoji: str
    desc: str
    enabled: bool = True
    structure: List[Dict[str, Any]]
    keywords: Optional[List[str]] = None
    bestFor: str
    color: str
    bgColor: str
    borderColor: str
    contentTypes: Optional[List[str]] = None
    hookTechniques: Optional[List[str]] = None
    topicMethods: Optional[List[str]] = None
    prototypes: Optional[List[str]] = None
    emotionCurve: Optional[str] = None


class DeconstructRules(BaseModel):
    script_template_recognition: Dict[str, Any]
    hook_pattern: Dict[str, Any]
    emotion_curve: Dict[str, Any]
    argument_structure: Dict[str, Any]
    visual_elements: Dict[str, Any]


class OriginalityThresholds(BaseModel):
    text_repeat_rate: int = Field(25, ge=10, le=50)
    structure_similarity: int = Field(40, ge=20, le=60)


class AdvancedSettings(BaseModel):
    script_template_preference: str = "auto"
    hybrid_strategy: str = "best_of_breed"
    force_replace_rule: str = "all"


class RemixAgentConfigPut(BaseModel):
    ip_id: str = Field(..., description="IP ID")
    templates: Optional[List[ScriptTemplate]] = None
    deconstruct_rules: Optional[DeconstructRules] = None
    originality_thresholds: Optional[OriginalityThresholds] = None
    advanced_settings: Optional[AdvancedSettings] = None


class RemixAgentConfigResponse(BaseModel):
    ip_id: str
    templates: List[Dict[str, Any]]
    deconstruct_rules: Dict[str, Any]
    originality_thresholds: Dict[str, Any]
    advanced_settings: Dict[str, Any]
    version: int
    updated_at: datetime


# ----- 辅助函数 -----

def _get_or_create_config(db: Session, ip_id: str, user_id: str = "system") -> RemixAgentConfig:
    """获取或创建默认配置"""
    config = db.query(RemixAgentConfig).filter(RemixAgentConfig.ip_id == ip_id).first()
    if not config:
        config = RemixAgentConfig(
            config_id=f"remix_cfg_{uuid.uuid4().hex[:12]}",
            ip_id=ip_id,
            templates=DEFAULT_SCRIPT_TEMPLATES,
            deconstruct_rules=DEFAULT_DECONSTRUCT_RULES,
            originality_thresholds=DEFAULT_ORIGINALITY_THRESHOLDS,
            advanced_settings=DEFAULT_ADVANCED_SETTINGS,
            version=1,
            updated_by=user_id,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


# ----- API 路由 -----

@router.get("/agent/remix/config", response_model=RemixAgentConfigResponse)
def get_remix_config(
    ip_id: str = Query(..., description="IP ID"),
    db: Session = Depends(get_db),
):
    """获取 Remix Agent 配置（不存在则返回默认）"""
    if not db.query(IP).filter(IP.ip_id == ip_id).first():
        raise HTTPException(status_code=404, detail=f"IP不存在: {ip_id}")
    
    config = _get_or_create_config(db, ip_id)
    return RemixAgentConfigResponse(
        ip_id=config.ip_id,
        templates=config.templates,
        deconstruct_rules=config.deconstruct_rules,
        originality_thresholds=config.originality_thresholds,
        advanced_settings=config.advanced_settings,
        version=config.version,
        updated_at=config.updated_at,
    )


@router.put("/agent/remix/config", response_model=RemixAgentConfigResponse)
def put_remix_config(
    payload: RemixAgentConfigPut,
    db: Session = Depends(get_db),
):
    """更新 Remix Agent 配置"""
    if not db.query(IP).filter(IP.ip_id == payload.ip_id).first():
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")
    
    config = db.query(RemixAgentConfig).filter(RemixAgentConfig.ip_id == payload.ip_id).first()
    
    if not config:
        # 创建新配置
        config = RemixAgentConfig(
            config_id=f"remix_cfg_{uuid.uuid4().hex[:12]}",
            ip_id=payload.ip_id,
            templates=[t.model_dump() for t in payload.templates] if payload.templates else DEFAULT_SCRIPT_TEMPLATES,
            deconstruct_rules=payload.deconstruct_rules.model_dump() if payload.deconstruct_rules else DEFAULT_DECONSTRUCT_RULES,
            originality_thresholds=payload.originality_thresholds.model_dump() if payload.originality_thresholds else DEFAULT_ORIGINALITY_THRESHOLDS,
            advanced_settings=payload.advanced_settings.model_dump() if payload.advanced_settings else DEFAULT_ADVANCED_SETTINGS,
            version=1,
            updated_by="user",
        )
        db.add(config)
    else:
        # 更新现有配置
        if payload.templates is not None:
            config.templates = [t.model_dump() for t in payload.templates]
        if payload.deconstruct_rules is not None:
            config.deconstruct_rules = payload.deconstruct_rules.model_dump()
        if payload.originality_thresholds is not None:
            config.originality_thresholds = payload.originality_thresholds.model_dump()
        if payload.advanced_settings is not None:
            config.advanced_settings = payload.advanced_settings.model_dump()
        config.version += 1
        config.updated_by = "user"
    
    db.commit()
    db.refresh(config)
    
    return RemixAgentConfigResponse(
        ip_id=config.ip_id,
        templates=config.templates,
        deconstruct_rules=config.deconstruct_rules,
        originality_thresholds=config.originality_thresholds,
        advanced_settings=config.advanced_settings,
        version=config.version,
        updated_at=config.updated_at,
    )


@router.post("/agent/remix/config/reset", response_model=RemixAgentConfigResponse)
def reset_remix_config(
    ip_id: str = Query(..., description="IP ID"),
    db: Session = Depends(get_db),
):
    """重置为默认配置"""
    if not db.query(IP).filter(IP.ip_id == ip_id).first():
        raise HTTPException(status_code=404, detail=f"IP不存在: {ip_id}")
    
    config = db.query(RemixAgentConfig).filter(RemixAgentConfig.ip_id == ip_id).first()
    if config:
        config.templates = DEFAULT_SCRIPT_TEMPLATES
        config.deconstruct_rules = DEFAULT_DECONSTRUCT_RULES
        config.originality_thresholds = DEFAULT_ORIGINALITY_THRESHOLDS
        config.advanced_settings = DEFAULT_ADVANCED_SETTINGS
        config.version += 1
        config.updated_by = "user"
        db.commit()
        db.refresh(config)
    else:
        config = _get_or_create_config(db, ip_id)
    
    return RemixAgentConfigResponse(
        ip_id=config.ip_id,
        templates=config.templates,
        deconstruct_rules=config.deconstruct_rules,
        originality_thresholds=config.originality_thresholds,
        advanced_settings=config.advanced_settings,
        version=config.version,
        updated_at=config.updated_at,
    )
