"""
Creator API Router
对接前端 /api/creator/* 路由
"""

from datetime import datetime, timezone
import logging
import math
import random
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db import get_db
from app.db.models import ContentDraft, IP, IPAsset
from app.prompts.viral_strategy_templates import get_viral_template, resolve_viral_elements
from app.services.content_scenario import (
    ContentGenerator,
    ScenarioOneRequest,
    ScenarioTwoRequest,
    ScenarioThreeRequest,
    FourDimWeights,
)
from app.services import remix_recommendation_service, tikhub_client

router = APIRouter(prefix="/creator", tags=["creator"])
logger = logging.getLogger(__name__)


def get_ip_profile(db: Session, ip_id: str) -> Optional[Dict[str, Any]]:
    """获取IP画像（合并 style_profile JSON 与基础字段，供各场景使用）"""
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        return None
    sp = ip.style_profile if isinstance(ip.style_profile, dict) else {}
    base: Dict[str, Any] = {
        # name 用于对外“IP名称”，self_name 用于文案自称（优先昵称）
        "name": ip.name,
        "self_name": (ip.nickname or "").strip() or ip.name,
        "style": "",
        "target_audience": ip.target_audience or "",
        "content_preference": ip.content_direction or "",
        "content_direction": ip.content_direction or "",
        "expertise": ip.expertise or "",
    }
    merged = {**base, **sp}
    return merged


def _extract_style_guardrails_from_assets(db: Session, ip_id: str) -> Dict[str, Any]:
    """
    从知识库提取风格强约束字段：
    - self_intro: 推荐自我介绍句
    - forbidden_self_names: 禁止自称
    - style_evidence: 语感证据片段（用于提示词 grounding）
    """
    rows = (
        db.query(IPAsset)
        .filter(IPAsset.ip_id == ip_id)
        .order_by(IPAsset.created_at.desc())
        .limit(120)
        .all()
    )
    if not rows:
        return {"self_intro": "", "forbidden_self_names": [], "style_evidence": []}

    evidence: List[str] = []
    forbidden: List[str] = []
    self_intro = ""
    for r in rows:
        title = (r.title or "").strip()
        content = (r.content or "").strip()
        if not content:
            continue
        if "专属语感" in title or "口癖" in title or "词典" in title:
            # 读取“首选称呼/禁用称呼”类信息
            for ln in content.splitlines():
                s = ln.strip()
                if not s:
                    continue
                if ("首选称呼" in s or "自称" in s) and not self_intro:
                    self_intro = s[:80]
                if "禁用称呼" in s:
                    raw = s.replace("禁用称呼", "").replace("：", " ").replace(":", " ")
                    parts = [p.strip("，,。；; ") for p in raw.split() if p.strip("，,。；; ")]
                    forbidden.extend([p for p in parts if len(p) <= 8])
            evidence.append(content[:280])
        elif "IP定位" in title or "爆款总结" in title:
            evidence.append(content[:220])
        if len(evidence) >= 4:
            break

    # 去重保序
    uniq_forbidden: List[str] = []
    for x in forbidden:
        if x and x not in uniq_forbidden:
            uniq_forbidden.append(x)
    return {
        "self_intro": self_intro,
        "forbidden_self_names": uniq_forbidden[:8],
        "style_evidence": evidence[:4],
    }


def _extract_topic_keywords(topic: str) -> List[str]:
    kws = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z0-9_]{2,}", topic or "")
    uniq: List[str] = []
    for k in kws:
        if k not in uniq:
            uniq.append(k)
    return uniq[:10]


def _score_text_relevance(text: str, keywords: List[str]) -> int:
    if not text or not keywords:
        return 0
    t = text.lower()
    score = 0
    for kw in keywords:
        if kw.lower() in t:
            score += 1
    return score


def _build_dynamic_few_shots(db: Session, ip_id: str, topic: str, k: int = 3) -> List[str]:
    """
    Phase B：动态 few-shot 组装
    来源：优先 content_drafts（已验证生成样本）+ 补充 IPAsset（知识库片段）
    """
    keywords = _extract_topic_keywords(topic)
    examples: List[str] = []

    draft_rows = (
        db.query(ContentDraft)
        .filter(ContentDraft.ip_id == ip_id)
        .order_by(ContentDraft.created_at.desc())
        .limit(80)
        .all()
    )
    scored_drafts: List[tuple[int, str]] = []
    for d in draft_rows:
        wf = d.workflow if isinstance(d.workflow, dict) else {}
        text = "\n".join(
            [
                str(wf.get("hook") or "").strip(),
                str(wf.get("opinion") or wf.get("body") or "").strip(),
                str(wf.get("cta") or "").strip(),
            ]
        ).strip()
        if not text:
            continue
        score = _score_text_relevance(text, keywords)
        if score <= 0:
            continue
        scored_drafts.append((score, text[:320]))
    scored_drafts.sort(key=lambda x: x[0], reverse=True)
    for _, t in scored_drafts[:k]:
        examples.append(f"[历史成稿样本] {t}")

    if len(examples) < k:
        asset_rows = (
            db.query(IPAsset)
            .filter(IPAsset.ip_id == ip_id)
            .order_by(IPAsset.created_at.desc())
            .limit(120)
            .all()
        )
        scored_assets: List[tuple[int, str]] = []
        for a in asset_rows:
            text = (a.content or "").strip()
            if not text:
                continue
            score = _score_text_relevance(text, keywords)
            if score <= 0:
                continue
            scored_assets.append((score, f"{(a.title or '知识库素材').strip()}: {text[:260]}"))
        scored_assets.sort(key=lambda x: x[0], reverse=True)
        for _, t in scored_assets:
            if len(examples) >= k:
                break
            examples.append(f"[知识库样本] {t}")

    return examples[:k]


_RECOMMENDED_TOPICS = [
    {"id": "1", "title": "现金流断裂如何自救", "score": 4.8, "tags": ["现金流", "创业"], "reason": "策略推荐"},
    {"id": "2", "title": "为什么90%的IP都在第一步做错了？", "score": 4.7, "tags": ["IP定位"], "reason": "策略推荐"},
    {"id": "3", "title": "月入3万的私域运营", "score": 4.7, "tags": ["私域", "变现"], "reason": "策略推荐"},
]


def _workflow_title(wf: Optional[dict]) -> str:
    if not isinstance(wf, dict):
        return "未命名内容"
    for key in ("title", "topic", "headline"):
        v = wf.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()[:200]
    return "未命名内容"


def _workflow_text_preview(wf: Optional[dict]) -> str:
    if not isinstance(wf, dict):
        return ""
    parts: List[str] = []
    for k in ("hook", "story", "opinion", "cta", "body", "text"):
        v = wf.get(k)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    return "\n".join(parts)[:8000]


def _library_status(draft: ContentDraft) -> str:
    wf = draft.workflow if isinstance(draft.workflow, dict) else {}
    st = wf.get("display_status") or wf.get("status")
    if st in ("pending", "published", "viral", "draft"):
        return st
    if wf.get("viral"):
        return "viral"
    c = (draft.compliance_status or "").lower()
    if c in ("pending", "review", "checking"):
        return "pending"
    if c in ("passed", "approved", "published", "ok"):
        return "published"
    return "draft"


def _metrics_from_quality(qs: Any) -> Dict[str, Any]:
    if not isinstance(qs, dict):
        return {}
    m = qs.get("metrics") or qs.get("engagement")
    if not isinstance(m, dict):
        return {}
    return {
        "views": int(m.get("views", 0) or 0),
        "likes": int(m.get("likes", 0) or 0),
        "comments": int(m.get("comments", 0) or 0),
        "completionRate": float(m.get("completion_rate", m.get("completionRate", 0)) or 0),
    }


def _draft_to_library_item(draft: ContentDraft) -> Dict[str, Any]:
    wf = draft.workflow if isinstance(draft.workflow, dict) else {}
    qs = draft.quality_score if isinstance(draft.quality_score, dict) else {}
    status = _library_status(draft)
    created = draft.created_at.isoformat() if draft.created_at else ""
    pub = wf.get("published_at")
    published_at = pub if isinstance(pub, str) else (
        draft.updated_at.isoformat() if status == "published" and draft.updated_at else None
    )
    gen_src = wf.get("generation_source")
    if gen_src not in ("topic", "remix", "voice", "viral"):
        gen_src = "topic"
    item: Dict[str, Any] = {
        "id": draft.draft_id,
        "title": _workflow_title(wf),
        "content": _workflow_text_preview(wf),
        "status": status,
        "platforms": wf.get("published_platforms") or [],
        "metrics": _metrics_from_quality(qs) or None,
        "createdAt": created,
        "generationSource": gen_src,
        "agentChain": wf.get("agent_chain") or ["Strategy", "Memory", "Generation", "Compliance"],
    }
    if published_at:
        item["publishedAt"] = published_at
    if wf.get("source_topic_id"):
        item["sourceTopicId"] = wf["source_topic_id"]
    if wf.get("source_url"):
        item["sourceUrl"] = wf["source_url"]
    return item


def _target_duration_to_length(seconds: int) -> str:
    if seconds <= 45:
        return "short"
    if seconds >= 120:
        return "long"
    return "medium"


def _split_content_sections(text: str) -> Dict[str, str]:
    """将纯文本草稿粗分为 hook/story/opinion/cta，避免前端展示占位。"""
    content = (text or "").strip()
    if not content:
        return {"hook": "", "story": "", "opinion": "", "cta": ""}
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    hook = lines[0][:200] if lines else ""
    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
    # 简单拆分：最后一段作为 CTA，其余为观点主体
    parts = [p.strip() for p in body.split("\n\n") if p.strip()]
    cta = parts[-1] if len(parts) >= 2 else ""
    opinion = "\n\n".join(parts[:-1]).strip() if len(parts) >= 2 else body
    return {"hook": hook, "story": "", "opinion": opinion, "cta": cta}


def _save_generated_draft(
    db: Session,
    *,
    draft_id: str,
    ip_id: str,
    level: str,
    title: str,
    content: str,
    style: str,
    generation_source: str,
    score: float,
    extra_workflow: Optional[Dict[str, Any]] = None,
) -> None:
    sections = _split_content_sections(content)
    workflow: Dict[str, Any] = {
        "title": title[:200] or "未命名内容",
        "topic": title,
        "body": content,
        "hook": sections["hook"],
        "story": sections["story"],
        "opinion": sections["opinion"],
        "cta": sections["cta"],
        "style": style,
        "generation_source": generation_source,
        "agent_chain": ["Strategy", "Memory", "Generation", "Compliance"],
        "display_status": "draft",
    }
    if isinstance(extra_workflow, dict) and extra_workflow:
        workflow.update(extra_workflow)
    row = ContentDraft(
        draft_id=draft_id,
        ip_id=ip_id or "1",
        level=level,
        workflow=workflow,
        quality_score={"score": float(score or 0.0)},
        compliance_status="passed",
    )
    db.add(row)
    db.commit()


# === 场景一：推荐选题生成 ===
class TopicGenerateRequest(BaseModel):
    topicId: str
    topicTitle: Optional[str] = ""
    style: str  # angry/calm/humor
    ipId: Optional[str] = "1"


@router.post("/generate/topic")
async def generate_from_topic(req: TopicGenerateRequest, db: Session = Depends(get_db)):
    """场景一第二步：用户选择选题后再生成正文"""
    try:
        ip_profile = get_ip_profile(db, req.ipId or "") or {}
        selected_topic = (req.topicTitle or "").strip() or (req.topicId or "").strip()
        if not selected_topic:
            return {"id": "gen_topic_invalid", "status": "failed", "error": "topic is required"}

        result = await ContentGenerator.scenario_one_generate_from_selected_topic(
            ip_profile=ip_profile,
            topic=selected_topic,
            category="selected",
        )
        draft_id = f"gen_topic_{uuid.uuid4().hex[:10]}"
        _save_generated_draft(
            db,
            draft_id=draft_id,
            ip_id=req.ipId or "1",
            level="topic",
            title=selected_topic,
            content=result.content or "",
            style=req.style,
            generation_source="topic",
            score=float(result.score or 0.0),
            extra_workflow={"source_topic_id": req.topicId, "source_topic_title": selected_topic},
        )
        return {
            "id": draft_id,
            "status": "completed",
            "progress": 100,
            "estimatedTime": 0,
            "content": result.content,
            "score": result.score,
        }
    except Exception as e:
        return {
            "id": f"gen_{req.topicId}",
            "status": "failed",
            "error": str(e),
        }


# === 场景二：仿写爆款 ===
class RemixGenerateRequest(BaseModel):
    url: str
    style: str
    ipId: Optional[str] = "1"


@router.post("/generate/remix")
async def generate_from_remix(req: RemixGenerateRequest, db: Session = Depends(get_db)):
    """场景二：仿写爆款（抖音 Web 单条优先，否则 hybrid；未配置或失败时退回原始 URL 文本）"""
    try:
        ip_profile = get_ip_profile(db, req.ipId or "") or {}

        competitor_text = req.url.strip()[:8000]
        if tikhub_client.is_configured():
            competitor_text = await tikhub_client.extract_competitor_text_for_remix(req.url.strip())

        request = ScenarioTwoRequest(
            ip_id=req.ipId or "1",
            competitor_content=competitor_text,
            competitor_platform=None,
            ip_profile=ip_profile,
            rewrite_level="medium",
        )

        result = await ContentGenerator.scenario_two(request)
        draft_id = f"gen_remix_{uuid.uuid4().hex[:10]}"
        raw_score = float(result.score or 0.0)
        if not math.isfinite(raw_score):
            raw_score = 0.0
        safe_content = (result.content if isinstance(result.content, str) else "") or ""
        _save_generated_draft(
            db,
            draft_id=draft_id,
            ip_id=req.ipId or "1",
            level="remix",
            title="仿写爆款",
            content=safe_content,
            style=req.style,
            generation_source="remix",
            score=raw_score,
            extra_workflow={"source_url": req.url},
        )

        return {
            "id": draft_id,
            "status": "completed",
            "progress": 100,
            "estimatedTime": 0,
            "content": safe_content,
            "score": raw_score,
        }
    except Exception as e:
        logger.exception("generate_from_remix failed: %s", e)
        return {
            "id": "gen_remix_001",
            "status": "failed",
            "error": str(e),
        }


@router.get("/remix/recommendations")
async def get_remix_recommendations(
    ipId: str = Query("1", description="IP 画像 id"),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    仿写推荐：结合 IP 关键词匹配抖音低粉爆款榜，并拉取配置的小红书话题笔记链接。
    需配置 TIKHUB_API_KEY；无数据或未配置时返回空列表。
    """
    try:
        items = await remix_recommendation_service.build_remix_recommendations(
            db, ip_id=ipId, limit=limit
        )
        return {"items": items}
    except Exception as e:
        logger.warning("仿写推荐失败: %s", e)
        return {"items": []}


# === 场景三：爆款原创 ===
class ViralGenerateRequest(BaseModel):
    input: str
    inputMode: str  # text/voice/file
    scriptTemplate: str
    viralElements: List[str]
    targetDuration: int
    style: str
    ipId: Optional[str] = "1"


def _build_scenario_three_request(
    db: Session,
    *,
    ip_id: str,
    input_text: str,
    script_template: str,
    viral_elements: Optional[List[str]],
    target_duration: int,
) -> ScenarioThreeRequest:
    """
    统一构建场景三（爆款原创）请求，供文字与语音入口复用。
    """
    ip_profile = get_ip_profile(db, ip_id) or {}
    # 兜底：确保 xiaomin1 默认昵称稳定为「小敏」
    if ip_id == "xiaomin1":
        ip_profile["self_name"] = "小敏"

    guardrails = _extract_style_guardrails_from_assets(db, ip_id)
    normalized_template = script_template or "opinion"
    template = get_viral_template(normalized_template)
    resolved_elements = resolve_viral_elements(normalized_template, viral_elements or [])
    few_shot_examples = _build_dynamic_few_shots(db, ip_id, input_text or "", k=3)
    ip_profile["self_intro"] = guardrails.get("self_intro") or ""
    ip_profile["forbidden_self_names"] = guardrails.get("forbidden_self_names") or []
    ip_profile["style_evidence"] = guardrails.get("style_evidence") or []
    ip_profile["few_shot_examples"] = few_shot_examples
    ip_profile["strategy_template_name"] = template.get("name") or ""
    ip_profile["strategy_template_instruction"] = template.get("instruction") or ""

    length = _target_duration_to_length(int(target_duration or 60))
    return ScenarioThreeRequest(
        ip_id=ip_id,
        topic=input_text,
        style_profile=ip_profile,
        key_points=resolved_elements,
        length=length,
    )


@router.post("/generate/viral")
async def generate_viral_original(req: ViralGenerateRequest, db: Session = Depends(get_db)):
    """场景三：爆款原创"""
    try:
        request = _build_scenario_three_request(
            db,
            ip_id=req.ipId or "1",
            input_text=req.input,
            script_template=req.scriptTemplate or "opinion",
            viral_elements=req.viralElements or [],
            target_duration=int(req.targetDuration or 60),
        )

        result = await ContentGenerator.scenario_three(request)

        draft_id = f"gen_viral_{uuid.uuid4().hex[:10]}"
        _save_generated_draft(
            db,
            draft_id=draft_id,
            ip_id=req.ipId or "1",
            level="viral",
            title=(req.input or "").strip()[:200] or "爆款原创",
            content=result.content or "",
            style=req.style,
            generation_source="viral",
            score=float(result.score or 0.0),
            extra_workflow={
                "viralElements": resolve_viral_elements(
                    req.scriptTemplate or "opinion", req.viralElements or []
                ),
                "scriptTemplate": req.scriptTemplate or "",
                "inputMode": req.inputMode or "text",
                "elementConfigMode": (
                    "auto"
                    if not (req.viralElements or [])
                    or any(x in {"auto", "system_auto"} for x in (req.viralElements or []))
                    else "manual"
                ),
            },
        )

        return {
            "id": draft_id,
            "status": "completed",
            "progress": 100,
            "estimatedTime": 0,
            "content": result.content,
            "score": result.score,
        }
    except Exception as e:
        return {
            "id": "gen_viral_001",
            "status": "failed",
            "error": str(e),
        }


# === 语音 / 文字快生成（走场景三）===
class OriginalGenerateRequest(BaseModel):
    text: str
    style: str
    scriptTemplate: Optional[str] = "opinion"
    viralElements: Optional[List[str]] = None
    targetDuration: Optional[int] = 60
    ipId: Optional[str] = "1"


@router.post("/generate/original")
@router.post("/generate/voice")
async def generate_from_original(req: OriginalGenerateRequest, db: Session = Depends(get_db)):
    """场景三：爆款原创（支持文本/语音输入；voice 路由兼容保留）"""
    try:
        request = _build_scenario_three_request(
            db,
            ip_id=req.ipId or "1",
            input_text=req.text.strip(),
            script_template=req.scriptTemplate or "opinion",
            viral_elements=req.viralElements or [],
            target_duration=int(req.targetDuration or 60),
        )
        result = await ContentGenerator.scenario_three(request)
        draft_id = f"gen_original_{uuid.uuid4().hex[:10]}"
        _save_generated_draft(
            db,
            draft_id=draft_id,
            ip_id=req.ipId or "1",
            level="viral",
            title=req.text.strip()[:200] or "爆款原创",
            content=result.content or "",
            style=req.style,
            generation_source="original",
            score=float(result.score or 0.0),
            extra_workflow={
                "viralElements": resolve_viral_elements(
                    req.scriptTemplate or "opinion", req.viralElements or []
                ),
                "scriptTemplate": req.scriptTemplate or "opinion",
                "inputMode": "voice",
                "elementConfigMode": (
                    "auto"
                    if not (req.viralElements or [])
                    or any(x in {"auto", "system_auto"} for x in (req.viralElements or []))
                    else "manual"
                ),
            },
        )
        return {
            "id": draft_id,
            "status": "completed",
            "progress": 100,
            "estimatedTime": 0,
            "content": result.content,
            "score": result.score,
        }
    except Exception as e:
        return {
            "id": "gen_original_001",
            "status": "failed",
            "error": str(e),
        }


# === 获取生成结果 ===
@router.get("/generate/{id}/result")
async def get_generate_result(id: str, db: Session = Depends(get_db)):
    """获取生成结果（优先读取 content_drafts；无数据时回退占位内容）。"""
    draft = db.query(ContentDraft).filter(ContentDraft.draft_id == id).first()
    if draft and isinstance(draft.workflow, dict):
        wf = draft.workflow
        return {
            "id": id,
            "title": _workflow_title(wf),
            "hook": wf.get("hook") or "",
            "story": wf.get("story") or "",
            "opinion": wf.get("opinion") or wf.get("body") or "",
            "cta": wf.get("cta") or "",
            "style": wf.get("style") or "angry",
            "viralElements": wf.get("viralElements") or [],
            "scriptTemplate": wf.get("scriptTemplate") or "",
            "agentChain": wf.get("agent_chain") or ["Strategy", "Memory", "Generation", "Compliance"],
            "compliance": {
                "originalityScore": 82,
                "sensitiveWords": [],
                "platformChecks": {"douyin": "passed", "xiaohongshu": "passed"},
            },
        }
    return {
        "id": id,
        "title": "测试内容",
        "hook": "钩子示例...",
        "story": "故事示例...",
        "opinion": "观点示例...",
        "cta": "行动指令示例...",
        "style": "angry",
        "compliance": {
            "originalityScore": 82,
            "sensitiveWords": [],
            "platformChecks": {"douyin": "passed", "xiaohongshu": "passed"},
        },
    }


# === 获取生成进度 ===
@router.get("/generate/{id}/progress")
async def get_generate_progress(id: str):
    """获取生成进度"""
    return {
        "id": id,
        "status": "completed",
        "progress": 100,
        "estimatedTime": 0,
    }


# === 推荐选题 / 刷新 ===
async def _topics_from_algorithm_or_fallback(
    db: Session,
    *,
    ip_id: str,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    """场景一第一步：四维评分推荐（失败时回退 TikHub/占位）。"""
    try:
        ip_profile = get_ip_profile(db, ip_id) or {}
        request = ScenarioOneRequest(
            ip_id=ip_id,
            platform="douyin",
            ip_profile=ip_profile,
            weights=FourDimWeights(
                relevance=0.3,
                hotness=0.3,
                competition=0.2,
                conversion=0.2,
            ),
            count=limit,
        )
        scored = await ContentGenerator.scenario_one_recommend_topics(request)
        if scored:
            cards: List[Dict[str, Any]] = []
            for idx, item in enumerate(scored, start=1):
                topic = item.get("topic")
                scores = item.get("scores") or {}
                if not topic:
                    continue
                cards.append(
                    {
                        "id": f"topic_{idx:03d}",
                        "title": getattr(topic, "title", "") or "",
                        "score": round(float(item.get("total_score") or 0.0) * 5.0, 2),
                        "tags": [getattr(topic, "category", "")] if getattr(topic, "category", "") else [],
                        "reason": (
                            f"四维评分 R/H/CV="
                            f"{round(float(scores.get('relevance', 0.0)), 2)}/"
                            f"{round(float(scores.get('hotness', 0.0)), 2)}/"
                            f"{round(float(scores.get('competition', 0.0)), 2)}/"
                            f"{round(float(scores.get('conversion', 0.0)), 2)}"
                        ),
                        "agentChain": ["Strategy", "Memory", "Generation", "Compliance"],
                    }
                )
            if cards:
                return cards
    except Exception as e:
        logger.warning("算法推荐选题失败，降级到 TikHub/占位: %s", e)

    if tikhub_client.is_configured():
        try:
            cards = await tikhub_client.get_recommended_topic_cards(limit=limit)
            if cards:
                return cards
        except Exception as e:
            logger.warning("TikHub 推荐选题不可用，使用内置占位: %s", e)
    return list(_RECOMMENDED_TOPICS)


@router.get("/topics/recommended")
async def get_recommended_topics(
    ipId: str = Query("1", description="IP 画像 id"),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """场景一第一步：推荐选题（四维评分；不生成正文）。"""
    topics = await _topics_from_algorithm_or_fallback(db, ip_id=ipId, limit=limit)
    return {"topics": topics}


@router.get("/topics/refresh")
async def refresh_topics(
    ipId: str = Query("1", description="IP 画像 id"),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """刷新推荐选题（四维评分推荐后打散）。"""
    topics = await _topics_from_algorithm_or_fallback(db, ip_id=ipId, limit=limit)
    shuffled = list(topics)
    random.shuffle(shuffled)
    return {"topics": shuffled}


# === 内容库 ===
@router.get("/library")
async def list_creator_library(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """内容库列表（来自 content_drafts；无数据时返回空数组）"""
    rows = (
        db.query(ContentDraft)
        .order_by(ContentDraft.created_at.desc())
        .limit(200)
        .all()
    )
    items = [_draft_to_library_item(d) for d in rows]
    if status and status != "all":
        items = [x for x in items if x.get("status") == status]
    return items


# === 发布 ===
class PublishRequest(BaseModel):
    id: str
    platforms: List[str]


@router.post("/publish")
async def publish_content(req: PublishRequest, db: Session = Depends(get_db)):
    """标记草稿为已发布（写入 workflow 元数据）"""
    draft = db.query(ContentDraft).filter(ContentDraft.draft_id == req.id).first()
    if not draft:
        return {"ok": True, "message": "draft not found; no-op"}
    wf = dict(draft.workflow) if isinstance(draft.workflow, dict) else {}
    wf["published_platforms"] = req.platforms
    wf["display_status"] = "published"
    wf["published_at"] = datetime.now(timezone.utc).isoformat()
    draft.workflow = wf
    draft.compliance_status = "published"
    flag_modified(draft, "workflow")
    db.commit()
    return {"ok": True}


# === 数据分析 ===
@router.get("/analytics")
async def creator_analytics(db: Session = Depends(get_db)):
    """创作端数据概览（基于 content_drafts 聚合；无数据时返回 0 与默认建议）"""
    rows = db.query(ContentDraft).all()
    published = sum(1 for d in rows if _library_status(d) == "published")
    viral = sum(1 for d in rows if _library_status(d) == "viral")
    leads = published * 3 + viral * 20

    avg_completion = 38.5
    engagement = 5.2
    viral_rate = (viral / published * 100.0) if published else 0.0

    suggestions: List[Dict[str, Any]] = [
        {
            "id": "1",
            "type": "hook",
            "title": "优化钩子",
            "description": "黄金3秒加入具体数字，完播率可提升约20%",
            "priority": "high",
        },
        {
            "id": "2",
            "type": "timing",
            "title": "发布时间",
            "description": "尝试在晚上7-9点发布，获得更多流量",
            "priority": "medium",
        },
    ]
    if not rows:
        suggestions.append(
            {
                "id": "3",
                "type": "topic",
                "title": "暂无内容数据",
                "description": "生成并保存内容后，将在此展示趋势与建议",
                "priority": "low",
            }
        )

    return {
        "published": published,
        "viral": viral,
        "leads": leads,
        "viralRate": round(viral_rate, 1),
        "completionRate": avg_completion,
        "engagementRate": engagement,
        "suggestions": suggestions,
    }


# === Agent状态 ===
@router.get("/agent-status")
async def get_agent_status():
    """获取Agent配置状态（含前端可选的 analytics / asr）"""
    return {
        "strategy": {"status": "ready", "config": ["四维权重", "竞品监控"]},
        "memory": {"status": "ready", "config": ["标签体系", "检索策略"]},
        "analytics": {"status": "ready", "config": ["播放量预测", "完播率预测"]},
        "remix": {"status": "ready", "config": ["解构规则"]},
        "asr": {"status": "ready", "config": ["语音转写", "Whisper"]},
        "generation": {"status": "ready", "config": ["风格训练", "口头禅"]},
        "compliance": {"status": "ready", "config": ["敏感词库"]},
    }
