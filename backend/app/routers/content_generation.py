"""
内容生成API路由
基于LangChain的内容生成、热点分析、质量评分
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP
from app.services.content_generation_pipeline import (
    ContentGenerationPipeline,
    TopicStrategyAgent,
    QualityScorer,
    create_content_pipeline,
    create_strategy_agent,
)
from app.services.memory_config_service import get_ip as get_ip_model

router = APIRouter()


# ==================== Request/Response Models ====================

class GenerateContentRequest(BaseModel):
    ip_id: str
    topic: str = Field(..., description="要生成内容的话题/主题")
    reference_assets: Optional[List[str]] = Field(None, description="引用的素材ID列表")
    style_override: Optional[dict] = Field(None, description="风格覆盖配置")


class GenerateContentResponse(BaseModel):
    draft: str
    quality: dict
    topic: str


class TopicAnalysisRequest(BaseModel):
    ip_id: str
    topics: List[str] = Field(..., description="热点话题列表")


class TopicAnalysisResponse(BaseModel):
    recommended_topics: List[dict]
    analysis: str


class QualityScoreRequest(BaseModel):
    ip_id: str
    content: str


class QualityScoreResponse(BaseModel):
    originality: float
    style_match: float
    emotion_curve: float
    readability: float
    value: float
    overall: float
    issues: List[str]
    suggestions: List[str]


class BatchGenerateRequest(BaseModel):
    ip_id: str
    topics: List[str] = Field(..., description="批量生成的话题列表")


class RecommendTopicsRequest(BaseModel):
    ip_id: str
    count: int = Field(5, ge=1, le=20, description="推荐选题条数")


# ==================== API Endpoints ====================

@router.post("/content/generate", response_model=GenerateContentResponse)
def generate_content(
    payload: GenerateContentRequest,
    db: Session = Depends(get_db),
):
    """
    生成内容（完整管道）
    
    1. 检索IP相关素材
    2. 构建风格化提示词
    3. 生成初稿
    4. 质量评分
    """
    # 获取IP信息
    ip = db.query(IP).filter(IP.ip_id == payload.ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")
    
    # 构建IP画像（合并数据库中的风格画像）
    ip_profile = {
        "name": ip.name,
        "expertise": ip.expertise,
        "content_direction": ip.content_direction,
        "target_audience": ip.target_audience,
        "style_features": ip.bio or "专业",
        "vocabulary": ip.expertise or "",
        "tone": "专业亲切",
        "catchphrases": "",
    }
    sp = getattr(ip, "style_profile", None)
    if isinstance(sp, dict) and sp:
        voc = sp.get("vocabulary")
        if isinstance(voc, list) and voc:
            ip_profile["vocabulary"] = ", ".join(str(x) for x in voc[:40])
        cp = sp.get("catchphrases")
        if isinstance(cp, list) and cp:
            ip_profile["catchphrases"] = ", ".join(str(x) for x in cp[:15])
        if sp.get("tone"):
            ip_profile["tone"] = str(sp["tone"])
        bits = [ip.bio or ""]
        pats = sp.get("sentence_patterns")
        if isinstance(pats, list) and pats:
            bits.append("句式偏好: " + "，".join(str(x) for x in pats[:5]))
        if sp.get("emotion_curve"):
            bits.append("情感曲线: " + str(sp["emotion_curve"]))
        merged = " ".join(b for b in bits if b).strip()
        if merged:
            ip_profile["style_features"] = merged

    # 创建生成管道
    pipeline = create_content_pipeline(payload.ip_id, ip_profile)
    
    # 生成内容
    result = pipeline.generate_content(
        topic=payload.topic,
        reference_assets=payload.reference_assets,
    )
    
    return GenerateContentResponse(
        draft=result["draft"],
        quality=result["quality"],
        topic=result["topic"],
    )


@router.post("/content/topics/analyze", response_model=TopicAnalysisResponse)
def analyze_topics(
    payload: TopicAnalysisRequest,
    db: Session = Depends(get_db),
):
    """
    热点话题分析
    
    分析给定话题与IP的相关性，返回推荐选题
    """
    ip = db.query(IP).filter(IP.ip_id == payload.ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")
    
    ip_profile = {
        "name": ip.name,
        "expertise": ip.expertise or "",
        "content_direction": ip.content_direction or "",
        "target_audience": ip.target_audience or "",
        "unique_value_prop": ip.unique_value_prop or "",
    }

    agent = create_strategy_agent(payload.ip_id, ip_profile)
    result = agent.analyze_topics(payload.topics)

    return TopicAnalysisResponse(
        recommended_topics=result.get("recommended_topics", []),
        analysis=result.get("analysis") or "",
    )


@router.post("/content/topics/recommend")
def recommend_topics(
    payload: RecommendTopicsRequest,
    db: Session = Depends(get_db),
):
    """
    智能推荐选题
    
    基于 IP 画像由模型生成候选选题（无需外部热点 API）。
    """
    ip = db.query(IP).filter(IP.ip_id == payload.ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")

    ip_profile = {
        "name": ip.name,
        "expertise": ip.expertise or "",
        "content_direction": ip.content_direction or "",
        "target_audience": ip.target_audience or "",
        "unique_value_prop": ip.unique_value_prop or "",
    }

    agent = create_strategy_agent(payload.ip_id, ip_profile)
    result = agent.recommend_topics(count=payload.count)

    return {
        "ip_id": payload.ip_id,
        "recommendations": result.get("recommended_topics", []),
        "analysis": result.get("analysis", ""),
    }


@router.post("/content/quality/score", response_model=QualityScoreResponse)
def score_quality(
    payload: QualityScoreRequest,
    db: Session = Depends(get_db),
):
    """
    质量评分
    
    对生成的内容进行多维度质量评分
    """
    if not get_ip_model(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")
    
    scorer = QualityScorer()
    result = scorer.score(payload.content)
    
    # 确保返回所有字段
    return QualityScoreResponse(
        originality=result.get("originality", 0.8),
        style_match=result.get("style_match", 0.8),
        emotion_curve=result.get("emotion_curve", 0.8),
        readability=result.get("readability", 0.8),
        value=result.get("value", 0.8),
        overall=result.get("overall", 0.8),
        issues=result.get("issues", []),
        suggestions=result.get("suggestions", []),
    )


@router.post("/content/batch/generate")
def batch_generate_content(
    payload: BatchGenerateRequest,
    db: Session = Depends(get_db),
):
    """
    批量生成内容
    
    一次生成多个话题的内容
    """
    ip = db.query(IP).filter(IP.ip_id == payload.ip_id).first()
    if not ip:
        raise HTTPException(status_code=404, detail=f"IP不存在: {payload.ip_id}")
    
    ip_profile = {
        "name": ip.name,
        "expertise": ip.expertise,
        "content_direction": ip.content_direction,
        "target_audience": ip.target_audience,
        "style_features": ip.bio or "专业",
        "vocabulary": ip.expertise or "",
        "tone": "专业亲切",
        "catchphrases": "",
    }
    sp = getattr(ip, "style_profile", None)
    if isinstance(sp, dict) and sp:
        voc = sp.get("vocabulary")
        if isinstance(voc, list) and voc:
            ip_profile["vocabulary"] = ", ".join(str(x) for x in voc[:40])
        cp = sp.get("catchphrases")
        if isinstance(cp, list) and cp:
            ip_profile["catchphrases"] = ", ".join(str(x) for x in cp[:15])
        if sp.get("tone"):
            ip_profile["tone"] = str(sp["tone"])
        bits = [ip.bio or ""]
        pats = sp.get("sentence_patterns")
        if isinstance(pats, list) and pats:
            bits.append("句式偏好: " + "，".join(str(x) for x in pats[:5]))
        if sp.get("emotion_curve"):
            bits.append("情感曲线: " + str(sp["emotion_curve"]))
        merged = " ".join(b for b in bits if b).strip()
        if merged:
            ip_profile["style_features"] = merged

    pipeline = create_content_pipeline(payload.ip_id, ip_profile)
    results = pipeline.batch_generate(payload.topics)
    
    return {
        "ip_id": payload.ip_id,
        "total": len(results),
        "results": [
            {
                "topic": r["topic"],
                "draft": r["draft"],
                "quality": r["quality"],
            }
            for r in results
        ],
    }
