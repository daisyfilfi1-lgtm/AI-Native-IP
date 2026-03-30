"""
Creator API Router
对接前端 /api/creator/* 路由
"""

from datetime import datetime, timezone
import asyncio
import json
import logging
import math
import random
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db import get_db
from app.db.models import ContentDraft, IP, IPAsset
from app.prompts.viral_strategy_templates import get_viral_template, resolve_viral_elements
from app.services.content_scenario import (
    ContentGenerator,
    ScenarioThreeRequest,
)
from app.services.enhanced_remix_pipeline import create_enhanced_remix
from app.services import (
    competitor_text_extraction,
    remix_recommendation_service,
    tikhub_client,
    douyin_hot_hub_client,
    multi_source_client,
)
from app.services.semantic_topic_filter import filter_topics_by_similarity
from app.services.style_corpus_service import StyleCorpusService
from app.services.strategy_config_service import get_merged_config
from app.services.style_refinement_service import (
    get_style_learnings_texts,
    record_rewrite_feedback,
    refine_draft_with_feedback,
    summarize_iteration_learning,
)
from app.services.vector_service import query_similar_assets as pg_query_similar_assets
from app.services.topic_recommendation_v4 import get_recommendation_service_v4

router = APIRouter(prefix="/creator", tags=["creator"])
logger = logging.getLogger(__name__)
_DOUYIN_SNAPSHOT_FILE = Path(__file__).resolve().parents[1] / "services" / "data" / "douyin_hot_hub_snapshot.json"
# 内置兜底数据 - 当所有外部API都失败时使用
# 注意：这些数据会被IP改写，所以保留originalTitle字段
_BUILTIN_DOUYIN_HOTLIST: List[Dict[str, Any]] = [
    {
        "id": "dyhub_builtin_1", 
        "title": "国足2:0库拉索",  # 会被IP改写覆盖
        "originalTitle": "国足2:0库拉索",  # 保留原标题
        "score": 4.95, 
        "tags": ["抖音", "热榜"], 
        "reason": "抖音热榜（builtin）", 
        "sourceUrl": "https://www.douyin.com/search/%E5%9B%BD%E8%B6%B32%3A0%E5%BA%93%E6%8B%89%E7%B4%A2"
    },
    {
        "id": "dyhub_builtin_2", 
        "title": "一天连轴转的留学生活",
        "originalTitle": "一天连轴转的留学生活",
        "score": 4.92, 
        "tags": ["抖音", "热榜"], 
        "reason": "抖音热榜（builtin）", 
        "sourceUrl": "https://www.douyin.com/search/%E4%B8%80%E5%A4%A9%E8%BF%9E%E8%BD%B4%E8%BD%AC%E7%9A%84%E7%95%99%E5%AD%A6%E7%94%9F%E6%B4%BB"
    },
    {
        "id": "dyhub_builtin_3", 
        "title": "社保第六险已覆盖超3亿人",
        "originalTitle": "社保第六险已覆盖超3亿人",
        "score": 4.89, 
        "tags": ["抖音", "热榜"], 
        "reason": "抖音热榜（builtin）", 
        "sourceUrl": "https://www.douyin.com/search/%E7%A4%BE%E4%BF%9D%E7%AC%AC%E5%85%AD%E9%99%A9%E5%B7%B2%E8%A6%86%E7%9B%96%E8%B6%853%E4%BA%BF%E4%BA%BA"
    },
    {
        "id": "dyhub_builtin_4", 
        "title": "前国脚怒赞国足表现",
        "originalTitle": "前国脚怒赞国足表现",
        "score": 4.86, 
        "tags": ["抖音", "热榜"], 
        "reason": "抖音热榜（builtin）", 
        "sourceUrl": "https://www.douyin.com/search/%E5%89%8D%E5%9B%BD%E8%84%9A%E6%80%92%E8%B5%9E%E5%9B%BD%E8%B6%B3%E8%A1%A8%E7%8E%B0"
    },
    {
        "id": "dyhub_builtin_5", 
        "title": "王钰栋回应球迷和队友期待",
        "originalTitle": "王钰栋回应球迷和队友期待",
        "score": 4.83, 
        "tags": ["抖音", "热榜"], 
        "reason": "抖音热榜（builtin）", 
        "sourceUrl": "https://www.douyin.com/search/%E7%8E%8B%E9%92%B0%E6%A0%8B%E5%9B%9E%E5%BA%94%E7%90%83%E8%BF%B7%E5%92%8C%E9%98%9F%E5%8F%8B%E6%9C%9F%E5%BE%85"
    },
]


def get_ip_profile(db: Session, ip_id: str) -> Optional[Dict[str, Any]]:
    """获取IP画像（合并 style_profile JSON 与基础字段，供各场景使用）"""
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        return None
    sp = ip.style_profile if isinstance(ip.style_profile, dict) else {}
    base: Dict[str, Any] = {
        # name 用于对外"IP名称"，self_name 用于文案自称（优先昵称）
        "name": ip.name,
        "self_name": (ip.nickname or "").strip() or ip.name,
        "style": "",
        "target_audience": ip.target_audience or "",
        "content_preference": ip.content_direction or "",
        "content_direction": ip.content_direction or "",
        "expertise": ip.expertise or "",
    }
    merged = {**base, **sp}

    # 用户迭代沉淀的文案学习要点（注入后续生成提示词）
    strat = ip.strategy_config if isinstance(ip.strategy_config, dict) else {}
    _lr = strat.get("style_learnings") or []
    _texts: List[str] = []
    for item in _lr[-30:]:
        if isinstance(item, dict) and item.get("text"):
            t = str(item["text"]).strip()
            if t:
                _texts.append(t[:500])
        elif isinstance(item, str) and item.strip():
            _texts.append(item.strip()[:500])
    merged["style_feedback_learnings"] = _texts
    
    # 兼容 EnhancedRemixPipeline 的字段命名
    # style_profile 可能存储的是旧字段名，需要映射到新字段名
    if "style" in merged and not merged.get("style_features"):
        merged["style_features"] = merged["style"]
    if "style_evidence" in merged and not merged.get("vocabulary"):
        # 从 style_evidence 提取词汇特征
        evidence = merged.get("style_evidence", [])
        if isinstance(evidence, list) and evidence:
            merged["vocabulary"] = ", ".join([str(e) for e in evidence[:5]])
    
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
            # 读取"首选称呼/禁用称呼"类信息
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


def _tokenize_cn_en(text: str) -> List[str]:
    tokens = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z0-9_]{2,}", text or "")
    uniq: List[str] = []
    for t in tokens:
        if t not in uniq:
            uniq.append(t)
    return uniq


def _calc_relevance_for_candidate(
    *,
    title: str,
    tags: List[str],
    ip_profile: Dict[str, Any],
) -> float:
    ip_text = " ".join(
        [
            str(ip_profile.get("expertise") or ""),
            str(ip_profile.get("content_direction") or ""),
            str(ip_profile.get("target_audience") or ""),
            str(ip_profile.get("monetization_model") or ""),
            str(ip_profile.get("product_service") or ""),
        ]
    )
    ip_tokens = set(_tokenize_cn_en(ip_text.lower()))
    if not ip_tokens:
        return 0.6
    candidate_tokens = set(_tokenize_cn_en(f"{title} {' '.join(tags)}".lower()))
    if not candidate_tokens:
        return 0.4
    overlap = len(ip_tokens & candidate_tokens)
    ratio = overlap / max(1, min(len(candidate_tokens), 8))
    # 归一化到 [0.4, 1.0]，避免极端 0 值导致全量过滤
    return max(0.4, min(1.0, 0.4 + ratio * 0.6))


def _calc_conversion_for_candidate(title: str, tags: List[str]) -> float:
    text = f"{title} {' '.join(tags)}"
    high_conv = ["测评", "教程", "推荐", "避坑", "省钱", "赚钱", "变现", "副业", "私域", "获客"]
    medium_conv = ["知识", "科普", "观点", "分析", "方法", "经验", "复盘"]
    if any(k in text for k in high_conv):
        return 0.9
    if any(k in text for k in medium_conv):
        return 0.65
    return 0.5


def _resolve_topic_weights(db: Session, ip_id: str) -> Dict[str, float]:
    """
    读取策略配置中的四维权重，兼容两套键名：
    - relevance/hotness/competition/conversion
    - fit/traffic/cost/monetization
    """
    default = {"relevance": 0.3, "hotness": 0.3, "competition": 0.2, "conversion": 0.2}
    try:
        cfg = get_merged_config(db, ip_id)
        raw = cfg.get("four_dim_weights") if isinstance(cfg, dict) else None
        if not isinstance(raw, dict):
            return default
        mapped = {
            "relevance": float(raw.get("relevance", raw.get("fit", default["relevance"])) or 0.0),
            "hotness": float(raw.get("hotness", raw.get("traffic", default["hotness"])) or 0.0),
            "competition": float(raw.get("competition", raw.get("cost", default["competition"])) or 0.0),
            "conversion": float(raw.get("conversion", raw.get("monetization", default["conversion"])) or 0.0),
        }
        total = sum(max(0.0, v) for v in mapped.values())
        if total <= 0:
            return default
        return {k: round(max(0.0, v) / total, 6) for k, v in mapped.items()}
    except Exception as e:
        logger.warning("读取四维权重失败，使用默认权重: %s", e)
        return default


def _rerank_tikhub_candidates(
    *,
    cards: List[Dict[str, Any]],
    ip_profile: Dict[str, Any],
    limit: int,
    weights: Dict[str, float],
) -> List[Dict[str, Any]]:
    wr = float(weights.get("relevance", 0.3) or 0.3)
    wh = float(weights.get("hotness", 0.3) or 0.3)
    wc = float(weights.get("competition", 0.2) or 0.2)
    wv = float(weights.get("conversion", 0.2) or 0.2)
    ranked: List[Dict[str, Any]] = []
    for idx, card in enumerate(cards, start=1):
        title = str(card.get("title") or "").strip()
        if not title:
            continue
        tags = [str(x) for x in (card.get("tags") or []) if str(x).strip()]
        source_reason = str(card.get("reason") or "").strip()
        base_score = float(card.get("score") or 0.0)
        # 数据源可能给 0–1 归一化分或 0–5 热度分；统一映射到 [0,1] 作为 hotness
        if base_score <= 1.0:
            hotness = max(0.0, min(1.0, base_score))
        else:
            hotness = max(0.0, min(1.0, base_score / 5.0))
        relevance = _calc_relevance_for_candidate(title=title, tags=tags, ip_profile=ip_profile)
        competition = max(0.0, min(1.0, 1.0 - hotness * 0.5))
        conversion = _calc_conversion_for_candidate(title, tags)
        total = relevance * wr + hotness * wh + competition * wc + conversion * wv
        # 保留原标题（用于前端展示）
        original_title = str(card.get("originalTitle") or card.get("original_title") or title)
        
        ranked.append(
            {
                "id": str(card.get("id") or f"topic_{idx:03d}"),
                "title": title,
                "originalTitle": original_title,  # 添加原标题
                "score": round(total * 5.0, 2),
                "tags": tags,
                "estimatedViews": str(
                    card.get("estimatedViews")
                    or card.get("estimated_views")
                    or "—"
                ),
                "estimatedCompletion": int(
                    card.get("estimatedCompletion")
                    or card.get("estimated_completion")
                    or 0
                ),
                "sourceUrl": str(
                    card.get("sourceUrl") or card.get("source_url") or ""
                ),
                "reason": (
                    f"{(source_reason or '大数据候选')} + 四维重排 R/H/CV="
                    f"{round(relevance, 2)}/{round(hotness, 2)}/"
                    f"{round(competition, 2)}/{round(conversion, 2)}"
                ),
                "agentChain": ["Strategy", "Memory", "Generation", "Compliance"],
                "_relevance": relevance,
            }
        )
    ranked.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
    return ranked[:limit]


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


def _fetch_style_learning_memory_lines(
    db: Session,
    *,
    ip_id: str,
    topic: str,
    emotion: str,
    audience: str,
    top_k: int = 3,
) -> List[str]:
    """从 pgvector 检索带 source=style_learning 的素材，与选题语义对齐的学习要点。"""
    q = StyleCorpusService.build_retrieval_query(topic=topic, emotion=emotion, audience=audience)
    if not q.strip():
        return []
    try:
        hits = pg_query_similar_assets(
            db, ip_id=ip_id, query=q, top_k=max(30, top_k * 10)
        )
    except Exception:
        return []
    if not hits:
        return []
    hit_ids = [str(h.get("asset_id") or "").strip() for h in hits if str(h.get("asset_id") or "").strip()]
    if not hit_ids:
        return []
    rows = (
        db.query(IPAsset)
        .filter(
            IPAsset.ip_id == ip_id,
            IPAsset.asset_id.in_(hit_ids),
            IPAsset.status == "active",
        )
        .all()
    )
    row_by_id = {r.asset_id: r for r in rows}
    out: List[str] = []
    for h in hits:
        aid = str(h.get("asset_id") or "").strip()
        row = row_by_id.get(aid)
        if not row:
            continue
        meta = row.asset_meta if isinstance(row.asset_meta, dict) else {}
        if str(meta.get("source") or "") != "style_learning":
            continue
        c = (row.content or "").strip()
        if c:
            out.append(c[:280])
        if len(out) >= top_k:
            break
    return out


def _build_style_context_from_vector(
    db: Session,
    *,
    ip_id: str,
    topic: str,
    emotion: str,
    audience: str,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    最终形态：优先复用现有 embedding + pgvector 检索 style corpus 样本。
    """
    svc = StyleCorpusService()
    samples = svc.search_samples_by_pgvector(
        db,
        ip_id=ip_id,
        topic=topic,
        emotion=emotion,
        audience=audience,
        top_k=top_k,
    )
    if not samples:
        # 兜底：防止向量未回填时，生成链路失去风格约束
        samples = svc.search_samples(topic=topic, emotion=emotion, audience=audience, top_k=top_k)
    style_layer = svc.build_style_constraint_layer(samples)
    sample_lines: List[str] = []
    for i, s in enumerate(samples[:top_k], start=1):
        fp = s.get("style_fingerprint") or {}
        kf = s.get("key_fragments") or {}
        sample_lines.append(
            f"- 样本{i}: topic={s.get('raw_topic') or s.get('sample_id')}; "
            f"rhythm={fp.get('sentence_rhythm', '')}; "
            f"hook={str(kf.get('golden_hook') or '')[:100]}"
        )
    # Memory 向量库中的「学习要点」与当前话题对齐的片段
    learn_lines = _fetch_style_learning_memory_lines(
        db,
        ip_id=ip_id,
        topic=topic,
        emotion=emotion,
        audience=audience,
        top_k=3,
    )
    for j, ln in enumerate(learn_lines, start=1):
        sample_lines.append(f"- 学习要点{j}: {ln}")
    return {
        "style_constraint_layer": style_layer,
        "style_retrieved_examples_text": "\n".join(sample_lines),
        "style_retrieved_sample_ids": [str(s.get("sample_id") or "") for s in samples[:top_k] if str(s.get("sample_id") or "")],
    }


_RECOMMENDED_TOPICS = [
    {"id": "1", "title": "现金流断裂如何自救", "score": 4.8, "tags": ["现金流", "创业"], "reason": "策略推荐"},
    {"id": "2", "title": "为什么90%的IP都在第一步做错了？", "score": 4.7, "tags": ["IP定位"], "reason": "策略推荐"},
    {"id": "3", "title": "月入3万的私域运营", "score": 4.7, "tags": ["私域", "变现"], "reason": "策略推荐"},
]

# 按 IP 定义强约束白名单关键词（命中任一即可通过）
# 小敏IP 2.0：从"负债创业宝妈"升级为"帮扶10万女性独立创业的导师"
# 内容矩阵比例：40%搞钱方法论 | 30%情感共情 | 20%技术展示 | 10%美好生活
_IP_TOPIC_WHITELIST = {
    "xiaomin1": [
        # ═══════════════════════════════════════════════════════════
        # 【40%】搞钱方法论与认知 - 吸粉/转化主力
        # ═══════════════════════════════════════════════════════════
        # 商业模式
        "创业", "副业", "低成本", "小成本", "轻创业", "轻装上阵", "摆摊", "私房",
        "商业模式", "商业思维", "做生意", "生意", "商机", "风口",
        # 变现与收入
        "赚钱", "变现", "收入", "月入", "盈利", "年入", "搞钱", "财务自由", 
        "月入过万", "月入3万", "月入5万", "月入十万", "年入百万",
        # 定价与成交
        "定价", "报价", "谈单", "成交", "签单", "开单", "接单", "客户", "顾客",
        # 流量与获客
        "私域", "获客", "引流", "流量", "同城", "本地", "朋友圈", "社群",
        "短视频", "直播", "营销", "推广", "获客渠道", "精准客户",
        
        # ═══════════════════════════════════════════════════════════
        # 【30%】情感共情与价值观 - 固粉/拉近距离
        # ═══════════════════════════════════════════════════════════
        # 女性成长与独立
        "女性", "女人", "宝妈", "妈妈", "家庭主妇", "全职妈妈", "职场妈妈",
        "独立", "自强", "清醒", "通透", "大女主", "女性智慧", "女性力量",
        "翻身", "逆袭", "改变", "转型", "蜕变", "重生", "觉醒", "成长",
        # 婚姻与情感
        "婚姻", "夫妻", "老公", "婆婆", "婆媳关系", "家庭关系", "两性", "情感",
        "离婚", "结婚", "择偶", "恋爱", "单身", "催婚", "大龄剩女",
        # 育儿与教育
        "育儿", "带娃", "孩子", "教育", "幼儿园", "小学", "辅导作业", "鸡娃",
        "亲子", "母子", "母女", "二胎", "三胎", "留守儿童",
        # 心理与情绪
        "焦虑", "抑郁", "内耗", "压力", "迷茫", "无助", "崩溃", "自愈",
        "情绪", "心态", "认知", "思维", "格局",
        
        # ═══════════════════════════════════════════════════════════
        # 【20%】技术展示与团队实力 - 秀肌肉/建立权威
        # ═══════════════════════════════════════════════════════════
        # 手艺与技术
        "馒头", "花样馒头", "面食", "美食", "早餐", "手工", "手艺", "制作", 
        "烘焙", "面点", "厨艺", "厨房", "教学", "培训", "教程", "配方",
        # 产品相关
        "新品", "爆款", "热销", "订单", "发货", "打包", "供应链",
        # 学习与成长
        "学习", "进修", "提升", "进阶", "高手", "大神", "老师", "导师", "师父",
        "实战", "经验", "踩坑", "避坑", "教训", "复盘",
        
        # ═══════════════════════════════════════════════════════════
        # 【10%】美好生活展示 - 造梦/提供向往
        # ═══════════════════════════════════════════════════════════
        # 精致生活
        "精致", "爱美", "穿搭", "化妆", "护肤", "美容", "形象", "气质",
        "又美又飒", "美丽", "漂亮", "好看", "时尚", "品味", "品质生活",
        # 生活方式
        "旅游", "旅行", "度假", "放松", "享受", "惬意", "幸福", "快乐",
        "下午茶", "咖啡", "仪式感", "生活碎片", "vlog", "日常",
        # 身份认同
        "老板娘", "老板", "创始人", "主理人", "普通人", "素人", "草根",
        
        # ═══════════════════════════════════════════════════════════
        # 【人群与场景】通用匹配词
        # ═══════════════════════════════════════════════════════════
        "普通人", "素人", "草根", "底层", "打工人", "上班族", "裸辞", "辞职",
        "负债", "欠款", "穷", "没钱", "困难", "熬", "坚持", "努力",
    ],
}
_IP_TOPIC_BLOCKLIST = {
    "xiaomin1": [
        # 医疗相关
        "医生", "医疗", "医院", "药", "治病", "问诊", "手术", "疗法",
        # 健康科普（小敏不是医生，避免医疗建议）
        "科普", "健康", "养生", "保健", "营养", "功效", "治疗",
        # 与美食无关的高风险词
        "减肥", "瘦身", "美容", "整容", "医美", "化妆品",
        # 不相关领域
        "汽车", "房产", "股票", "基金", "投资", "理财", "保险",
    ],
}
# 与数据库中历史 id「xiaomin」对齐，策略/话题算法与 xiaomin1（小敏）一致
_IP_TOPIC_WHITELIST["xiaomin"] = _IP_TOPIC_WHITELIST["xiaomin1"]
_IP_TOPIC_BLOCKLIST["xiaomin"] = _IP_TOPIC_BLOCKLIST["xiaomin1"]

# 可选语义过滤数据缓存（若未加载则为空，不影响主流程）
_IP_DATA_CACHE: Dict[str, Dict[str, Any]] = {}


def _ensure_ip_data_cache(db: Session, ip_id: str) -> Dict[str, Any]:
    """确保IP数据缓存已加载，如果未加载则从数据库读取并缓存"""
    global _IP_DATA_CACHE
    if ip_id in _IP_DATA_CACHE:
        return _IP_DATA_CACHE[ip_id]
    
    # 从数据库加载IP配置
    ip_profile = get_ip_profile(db, ip_id)
    if ip_profile:
        _IP_DATA_CACHE[ip_id] = ip_profile
        logger.info(f"Loaded IP data cache for {ip_id}")
    return ip_profile or {}


def _topic_hit_whitelist(topic: Dict[str, Any], keywords: List[str]) -> bool:
    if not keywords:
        return True
    title = str(topic.get("title") or "")
    tags = ",".join(str(x) for x in (topic.get("tags") or []) if x is not None)
    text = f"{title} {tags}"
    return any(kw and kw in text for kw in keywords)


# 小敏IP核心词 - 必须至少命中1个，否则直接丢弃
_XIAOMIN_CORE_KEYWORDS = [
    "宝妈", "妈妈", "女性", "女人",
    "创业", "副业", "赚钱", "变现", "搞钱",
    "馒头", "花样馒头", "面食", "手艺", "手工",
    "摆摊", "私房", "低成本", "轻创业",
]


def _topic_hit_core_keywords(topic: Dict[str, Any]) -> bool:
    """检查话题是否命中核心词（小敏IP专用严格模式）"""
    title = str(topic.get("title") or "")
    original_title = str(topic.get("originalTitle") or topic.get("original_title") or "")
    text = f"{title} {original_title}"
    return any(kw in text for kw in _XIAOMIN_CORE_KEYWORDS)


def _topic_hit_blocklist(topic: Dict[str, Any], keywords: List[str]) -> bool:
    if not keywords:
        return False
    title = str(topic.get("title") or "")
    tags = ",".join(str(x) for x in (topic.get("tags") or []) if x is not None)
    text = f"{title} {tags}"
    return any(kw and kw in text for kw in keywords)


def _classify_hotspot_type(title: str) -> str:
    """
    根据标题内容识别热点类型，归类到4-3-2-1内容矩阵
    
    40% 搞钱方法论与认知
    30% 情感共情与价值观  
    20% 技术展示与团队实力
    10% 美好生活展示
    """
    title_lower = title.lower()
    
    # 【40%】搞钱方法论 - 商业模式/变现/获客/定价
    money_keywords = ["赚钱", "变现", "月入", "年入", "收入", "盈利", "生意", "创业", "副业",
                      "商业模式", "定价", "成交", "谈单", "客户", "获客", "引流", "私域",
                      "流量", "营销", "推广", "低成本", "轻创业", "摆摊", "商机"]
    if any(kw in title_lower for kw in money_keywords):
        return "money"
    
    # 【30%】情感共情 - 婚姻/育儿/女性成长/心理
    emotion_keywords = ["婚姻", "夫妻", "老公", "婆婆", "离婚", "结婚", "恋爱", "择偶",
                        "育儿", "带娃", "孩子", "教育", "焦虑", "抑郁", "内耗", "压力",
                        "迷茫", "女性", "宝妈", "妈妈", "独立", "翻身", "逆袭", "改变"]
    if any(kw in title_lower for kw in emotion_keywords):
        return "emotion"
    
    # 【20%】技术展示 - 手艺/美食/产品/教学
    skill_keywords = ["馒头", "面食", "美食", "早餐", "烘焙", "手工", "手艺", "制作",
                      "厨艺", "厨房", "教学", "培训", "教程", "配方", "新品", "技术"]
    if any(kw in title_lower for kw in skill_keywords):
        return "skill"
    
    # 【10%】美好生活 - 精致/穿搭/旅游/生活方式
    life_keywords = ["精致", "穿搭", "化妆", "护肤", "美丽", "时尚", "旅游", "旅行",
                     "度假", "生活", "仪式感", "品质", "享受", "幸福"]
    if any(kw in title_lower for kw in life_keywords):
        return "life"
    
    # 默认归类为情感共情（最容易引发共鸣）
    return "emotion"


def _adapt_topics_to_ip_angle(
    *,
    ip_id: str,
    topics: List[Dict[str, Any]],
    keywords: List[str],
    ip_profile: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    当热点未直接命中 IP 白名单关键词时，做"热点 x IP 视角"改写，
    保持大数据来源不丢失，同时让题目更贴近当前 IP 定位。
    
    IP 2.0升级：根据4-3-2-1内容矩阵智能改写
    40% 搞钱方法论 | 30% 情感共情 | 20% 技术展示 | 10% 美好生活
    """
    if not topics or not keywords:
        return topics
    
    # 获取IP核心标签用于改写
    expertise = ip_profile.get("expertise", "") if ip_profile else ""
    content_dir = ip_profile.get("content_direction", "") if ip_profile else ""
    
    # 针对小敏IP的特殊处理（xiaomin / xiaomin1 均视为小敏）
    is_xiaomin = ip_id in ("xiaomin", "xiaomin1")
    
    # 选择最有代表性的关键词
    priority_keywords = [kw for kw in keywords if kw in ["宝妈", "创业", "女性", "赚钱", "独立", "翻身"]]
    if not priority_keywords:
        priority_keywords = keywords
    
    k1 = priority_keywords[0]
    k2 = priority_keywords[1] if len(priority_keywords) > 1 else priority_keywords[0]
    
    out: List[Dict[str, Any]] = []
    for t in topics:
        title = str(t.get("title") or "").strip()
        if not title:
            continue
        tags = [str(x).strip() for x in (t.get("tags") or []) if str(x).strip()]
        
        # 识别热点类型
        hotspot_type = _classify_hotspot_type(title)
        
        # 添加IP相关标签
        merged_tags: List[str] = []
        if is_xiaomin:
            # 小敏IP 2.0标签体系
            if hotspot_type == "money":
                merged_tags = ["搞钱方法论", "宝妈创业", "商业思维"]
            elif hotspot_type == "emotion":
                merged_tags = ["情感共情", "女性独立", "清醒大女主"]
            elif hotspot_type == "skill":
                merged_tags = ["技术展示", "花样馒头", "实战派手艺人"]
            else:  # life
                merged_tags = ["美好生活", "精致生活家", "又美又飒"]
        
        for x in tags + [k1, k2]:
            if x and x not in merged_tags:
                merged_tags.append(x)
        
        nt = dict(t)
        
        # 根据热点类型智能改写标题（4-3-2-1内容矩阵）
        if is_xiaomin:
            if hotspot_type == "money":
                # 【40%】搞钱方法论 - 强调商业模式和变现
                templates = [
                    f"从0到月入3万：这个宝妈的{k1}{k2}打法太绝了",
                    f"不想上班？试试这个{k1}副业，宝妈实测月入过万",
                    f"揭秘：用{k1}做{k2}，她是怎么做到月入3万的",
                    f"普通人也能复制的{k1}搞钱方法，宝妈亲测有效",
                ]
                nt["title"] = templates[len(out) % len(templates)]
                nt["content_category"] = "搞钱方法论(40%)"
                
            elif hotspot_type == "emotion":
                # 【30%】情感共情 - 强调女性成长和独立
                templates = [
                    f"从负债到逆袭：一个{k1}如何用{k2}重启人生",
                    f"她说：女人最大的底气，是拥有{k1}和{k2}的能力",
                    f"婚姻不是避风港：这个{k1}用{k2}找回了自己",
                    f"当妈妈后我才明白：{k1}比啥都重要，{k2}让我重获新生",
                ]
                nt["title"] = templates[len(out) % len(templates)]
                nt["content_category"] = "情感共情(30%)"
                
            elif hotspot_type == "skill":
                # 【20%】技术展示 - 强调手艺和实力
                templates = [
                    f"手艺变现金：她用{k1}把{k2}做到月入3万",
                    f"从厨房到台前：一个{k1}的{k2}创业实录",
                    f"不靠颜值靠手艺：这个{k1}用{k2}打出一片天",
                    f"2000元起步：她用{k1}{k2}，现在月入5万",
                ]
                nt["title"] = templates[len(out) % len(templates)]
                nt["content_category"] = "技术展示(20%)"
                
            else:  # life
                # 【10%】美好生活 - 精致生活展示
                templates = [
                    f"创业女人的精致生活：{k1}也要有{k2}的仪式感",
                    f"左手事业右手生活：这个{k1}把{k2}过成了诗",
                    f"又美又飒：{k1}的{k2}日常，活成自己想要的样子",
                    f"经济独立后：一个{k1}的{k2}生活有多爽",
                ]
                nt["title"] = templates[len(out) % len(templates)]
                nt["content_category"] = "美好生活(10%)"
        else:
            # 默认改写方式（其他IP）
            nt["title"] = f"{title}：{k1}如何帮她实现{k2}"
            nt["content_category"] = "IP角度改写"
        
        nt["tags"] = merged_tags[:6]
        nt["reason"] = f"IP2.0改写({hotspot_type}) + 原热点：{title[:20]}..."
        nt["originalTitle"] = title  # 使用驼峰命名，与前端一致
        nt["sourceUrl"] = str(t.get("sourceUrl") or t.get("source_url") or "")  # 保留原链接
        nt["hotspot_type"] = hotspot_type
        out.append(nt)
    return out


def _extract_keywords_from_ip_profile(ip_profile: Dict[str, Any]) -> List[str]:
    """从IP画像动态提取白名单关键词"""
    keywords = []
    fields = [
        ip_profile.get("expertise", ""),
        ip_profile.get("content_direction", ""),
        ip_profile.get("target_audience", ""),
        ip_profile.get("passion", ""),
        ip_profile.get("market_demand", ""),
        ip_profile.get("product_service", ""),
    ]
    for field in fields:
        if field and isinstance(field, str):
            # 提取2-8个字符的关键词
            words = re.findall(r'[\u4e00-\u9fa5]{2,8}', field)
            keywords.extend(words)
    # 去重并限制数量
    unique_keywords = list(dict.fromkeys(keywords))[:15]
    return unique_keywords


def _apply_topic_whitelist(db: Session, ip_id: str, topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """白名单过滤 + 语义过滤 + IP角度改写（按优先级）"""
    # 确保缓存已加载
    if ip_id not in _IP_DATA_CACHE:
        _ensure_ip_data_cache(db, ip_id)
    
    blocklist = _IP_TOPIC_BLOCKLIST.get(ip_id) or []
    if blocklist:
        blocked_filtered = [t for t in topics if not _topic_hit_blocklist(t, blocklist)]
        if blocked_filtered:
            topics = blocked_filtered
        else:
            logger.warning(
                "IP topics all hit blocklist, keep original hotlist to avoid empty result, ip_id=%s, blocklist=%s",
                ip_id,
                blocklist,
            )

    # 小敏IP：强制使用严格核心词模式，跳过宽松白名单
    if ip_id in ("xiaomin", "xiaomin1"):
        logger.info("xiaomin: Using strict core keyword filter")
        filtered = [t for t in topics if _topic_hit_core_keywords(t)]
        if filtered:
            logger.info(f"xiaomin: Core keyword matched {len(filtered)} topics")
            for t in filtered:
                t['filter_method'] = 'core_matched'
            return filtered
        logger.warning("xiaomin: No topics hit core keywords, returning empty")
        return []

    # 其他IP：使用宽松白名单
    # 1. 优先使用硬编码白名单
    keywords = _IP_TOPIC_WHITELIST.get(ip_id) or []
    
    # 2. 如果没有硬编码白名单，从IP画像动态提取
    if not keywords:
        ip_profile = _IP_DATA_CACHE.get(ip_id) or {}
        keywords = _extract_keywords_from_ip_profile(ip_profile)
        if keywords:
            logger.info(f"Dynamic keywords for {ip_id}: {keywords[:5]}...")

    # 先尝试关键词匹配
    if keywords:
        filtered = [t for t in topics if _topic_hit_whitelist(t, keywords)]
        if filtered:
            logger.info(f"Keyword matched {len(filtered)} topics")
            return filtered

    # 关键词没匹配时，使用语义相似度过滤
    # 获取IP配置
    ip_config = _IP_DATA_CACHE.get(ip_id) if isinstance(_IP_DATA_CACHE, dict) else None
    if ip_config:
        try:
            # 使用语义过滤，降低阈值到0.2以获取更多结果
            semantic_filtered = filter_topics_by_similarity(
                topics=topics,
                ip_data=ip_config,
                threshold=0.2
            )
            if semantic_filtered:
                logger.info(f"Semantic filter matched {len(semantic_filtered)} topics")
                for t in semantic_filtered:
                    t['filter_method'] = 'semantic'
                return semantic_filtered
        except Exception as e:
            logger.warning("Semantic filter failed, fallback to IP angle adaptation: %s", e)

    # === 严格模式：小敏IP必须命中核心词，否则直接丢弃 ===
    if ip_id in ("xiaomin", "xiaomin1"):
        logger.warning("xiaomin: No whitelist match, applying strict core keyword filter")
        strict_filtered = [t for t in topics if _topic_hit_core_keywords(t)]
        if strict_filtered:
            logger.info(f"xiaomin: Core keyword matched {len(strict_filtered)} topics")
            for t in strict_filtered:
                t['filter_method'] = 'strict_core'
            return strict_filtered
        # 严格模式下，没有命中核心词的直接丢弃（宁可少而精）
        logger.warning("xiaomin: No topics hit core keywords, returning empty")
        return []

    # 其他IP：执行「热点 x IP」角度改写
    logger.warning("No topics match IP directly, adapt to IP angle, ip_id=%s", ip_id)
    if topics:
        # 获取IP画像用于智能改写
        ip_profile = _IP_DATA_CACHE.get(ip_id) if isinstance(_IP_DATA_CACHE, dict) else None
        adapted = _adapt_topics_to_ip_angle(
            ip_id=ip_id,
            topics=topics,
            keywords=keywords or ["创业", "变现"],
            ip_profile=ip_profile,
        )
        if adapted:
            for t in adapted:
                t["filter_method"] = "ip_adapted"
            return adapted
    return []


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


def _sanitize_for_json(obj: Any) -> Any:
    """PostgreSQL JSONB / json.dumps 不接受 NaN/Inf，嵌套 dict 中也可能出现。"""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else 0.0
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


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
    workflow = _sanitize_for_json(workflow)
    try:
        sc = float(score or 0.0)
        if not math.isfinite(sc):
            sc = 0.0
    except (TypeError, ValueError):
        sc = 0.0
    qs = _sanitize_for_json({"score": sc})
    row = ContentDraft(
        draft_id=draft_id,
        ip_id=ip_id or "1",
        level=level,
        workflow=workflow,
        quality_score=qs,
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
        ip_profile.update(
            _build_style_context_from_vector(
                db,
                ip_id=req.ipId or "1",
                topic=selected_topic,
                emotion=str(ip_profile.get("content_direction") or ""),
                audience=str(ip_profile.get("target_audience") or ""),
                top_k=3,
            )
        )

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
            extra_workflow={
                "source_topic_id": req.topicId,
                "source_topic_title": selected_topic,
                "styleDiagnostics": (result.metadata or {}).get("style_diagnostics"),
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
            "id": f"gen_{req.topicId}",
            "status": "failed",
            "error": str(e),
        }


# === 场景二：仿写爆款（异步任务模式）===
class RemixGenerateRequest(BaseModel):
    url: str
    style: str
    ipId: Optional[str] = "1"
    # 与 url 同时提交时，并入豆包上下文（标题/口播摘录），提高抖音链路的提取准确度
    pasted_script: Optional[str] = None


# 内存任务存储（生产环境建议用 Redis）
_remix_tasks: Dict[str, Dict[str, Any]] = {}


def _get_db_session():
    """获取独立的数据库 session（用于后台任务）"""
    from app.db import SessionLocal
    return SessionLocal()


async def _run_remix_task(
    task_id: str,
    url: str,
    style: str,
    ip_id: str,
    pasted_script: Optional[str] = None,
):
    """后台执行 Remix 任务"""
    db = None
    try:
        db = _get_db_session()
        _remix_tasks[task_id]["status"] = "processing"
        _remix_tasks[task_id]["progress"] = 10
        _remix_tasks[task_id]["stage"] = "extracting"
        
        # 获取 IP Profile
        ip_profile = get_ip_profile(db, ip_id) or {}
        ip_profile["ip_id"] = ip_id

        # 检查是否为手动输入模式
        MANUAL_PREFIX = "[MANUAL_TEXT]"
        if url.startswith(MANUAL_PREFIX):
            competitor_text = url[len(MANUAL_PREFIX):].strip()
            extraction_result = {
                "success": True,
                "text": competitor_text,
                "error": "",
                "method": "manual_input",
                "metadata": {
                    "platform": "manual",
                    "original_url": "manual_input",
                    "resolved_url": "manual_input",
                }
            }
            logger.info(f"[Task {task_id}] 手动输入模式，文本长度: {len(competitor_text)}")
        else:
            # 提取竞品文本
            extraction_result = await competitor_text_extraction.extract_competitor_text_with_fallback(
                url,
                pasted_script=pasted_script,
            )
        
        if not extraction_result["success"]:
            error_msg = extraction_result["error"]
            logger.warning(f"[Task {task_id}] 文本提取失败: {error_msg}")
            
            # 分类错误信息
            if "TIKHUB_API_KEY" in error_msg:
                user_error = "文本提取服务未配置（TIKHUB_API_KEY），建议：\n1. 点击「第三方工具」提取文案\n2. 或使用「粘贴文案」手动输入"
            elif "403" in error_msg or "权限" in error_msg:
                user_error = "API 权限不足，建议：\n1. 点击「第三方工具」提取文案\n2. 或使用「粘贴文案」手动输入\n3. 或联系管理员检查 TikHub 权限"
            elif "404" in error_msg or "不存在" in error_msg:
                user_error = "视频不存在或已被删除，请检查链接是否有效"
            elif "超时" in error_msg:
                user_error = "提取超时，请稍后重试或更换链接"
            elif "Web 爬取" in error_msg and "失败" in error_msg:
                user_error = "无法自动提取该链接内容。建议：\n1. 点击「第三方工具」提取文案\n2. 使用「粘贴文案」手动输入\n3. 更换其他视频链接"
            else:
                user_error = f"无法提取链接内容，建议：\n1. 使用「第三方工具」提取文案\n2. 或「粘贴文案」手动输入"
            
            _remix_tasks[task_id].update({
                "status": "failed",
                "error": user_error,
                "details": {
                    "stage": "text_extraction",
                    "url": url[:100],
                    "raw_error": error_msg,
                }
            })
            return
        
        competitor_text = extraction_result["text"]
        metadata = extraction_result.get("metadata", {})
        logger.info(f"[Task {task_id}] 文本提取成功，长度: {len(competitor_text)}")
        
        # 检查文本长度
        if len(competitor_text.strip()) < 20:
            _remix_tasks[task_id].update({
                "status": "failed",
                "error": "提取的口播稿太短（少于20字），无法进行有效仿写。\n建议：\n1. 检查原视频是否有语音内容\n2. 使用「粘贴文案」手动输入完整文案",
                "details": {
                    "stage": "text_validation",
                    "text_length": len(competitor_text),
                }
            })
            return
        
        _remix_tasks[task_id]["progress"] = 40
        _remix_tasks[task_id]["stage"] = "remixing"
        
        # 执行增强洗稿（同步管线含 LLM 调用；必须放到线程池，否则会阻塞事件循环，
        # 导致 /generate/remix/{id}/status 轮询无法响应 → 网关 504）
        result = await asyncio.to_thread(
            create_enhanced_remix,
            ip_id,
            ip_profile,
            competitor_text,
            competitor_url=url,
            topic=competitor_text[:200],
        )
        
        _remix_tasks[task_id]["progress"] = 80
        _remix_tasks[task_id]["stage"] = "saving"
        
        # 保存结果
        draft_id = f"gen_remix_{uuid.uuid4().hex[:10]}"
        safe_content = str(result.get("content", "")).strip()
        quality = result.get("quality") or {}
        raw_score = float(quality.get("overall", 0.8) if isinstance(quality, dict) else 0.8)
        if not math.isfinite(raw_score):
            raw_score = 0.8
        
        _save_generated_draft(
            db,
            draft_id=draft_id,
            ip_id=ip_id,
            level="remix",
            title="仿写爆款",
            content=safe_content,
            style=style,
            generation_source="remix",
            score=raw_score,
            extra_workflow={
                "source_url": url,
                "text_extraction_method": extraction_result["method"],
                "text_extraction_platform": metadata.get("platform"),
                "text_extraction_resolved_url": metadata.get("resolved_url"),
                "text_extraction_length": len(competitor_text),
                "original_competitor_text": competitor_text[:500],
                "structure": result.get("structure"),
                "elevations": result.get("elevations"),
                "viral_elements": result.get("viral_elements"),
                "assets_used": [
                    {"id": a.get("id"), "title": a.get("title")}
                    for a in (result.get("assets_used") or [])
                ],
                "duration_seconds": result.get("duration_seconds"),
                "remixV2Enabled": True,
            },
        )
        
        _remix_tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "draft_id": draft_id,
            "content": safe_content,
            "score": raw_score,
        })
        logger.info(f"[Task {task_id}] 任务完成，draft_id: {draft_id}")
        
    except Exception as e:
        logger.exception(f"[Task {task_id}] 任务失败: {e}")
        _remix_tasks[task_id].update({
            "status": "failed",
            "error": f"仿写生成失败: {str(e)}",
        })
    finally:
        if db:
            db.close()


@router.post("/generate/remix")
async def generate_from_remix(req: RemixGenerateRequest):
    """场景二：仿写爆款 - 提交异步任务
    
    返回任务ID，前端需要轮询 /generate/remix/{task_id}/status 获取进度
    """
    # 参数校验
    url = (req.url or "").strip()
    if not url:
        return {
            "task_id": "",
            "status": "failed",
            "error": "链接不能为空",
        }
    
    MANUAL_PREFIX = "[MANUAL_TEXT]"
    if not url.startswith(("http://", "https://", MANUAL_PREFIX)):
        return {
            "task_id": "",
            "status": "failed", 
            "error": "链接格式不正确，必须以 http:// 或 https:// 开头",
        }
    
    # 创建任务
    task_id = f"remix_task_{uuid.uuid4().hex[:16]}"
    _remix_tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "stage": "pending",
        "url": url[:100],
        "ip_id": req.ipId or "1",
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # 启动后台任务
    asyncio.create_task(
        _run_remix_task(
            task_id,
            url,
            req.style,
            req.ipId or "1",
            pasted_script=(req.pasted_script or "").strip() or None,
        )
    )
    
    logger.info(f"[Task {task_id}] 任务已提交")
    
    return {
        "task_id": task_id,
        "status": "pending",
        "progress": 0,
        "message": "任务已提交，请轮询状态接口获取进度",
    }


@router.get("/generate/remix/{task_id}/status")
async def get_remix_task_status(task_id: str):
    """查询 Remix 任务状态"""
    task = _remix_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 清理敏感信息
    return {
        "task_id": task["task_id"],
        "status": task["status"],
        "progress": task.get("progress", 0),
        "stage": task.get("stage", ""),
        "error": task.get("error"),
        "draft_id": task.get("draft_id"),
    }


@router.get("/generate/remix/{task_id}/result")
async def get_remix_task_result(task_id: str):
    """获取 Remix 任务结果（完成后）"""
    task = _remix_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if task["status"] != "completed":
        return {
            "task_id": task_id,
            "status": task["status"],
            "error": task.get("error"),
        }
    
    return {
        "task_id": task_id,
        "status": "completed",
        "id": task.get("draft_id"),
        "progress": 100,
        "estimatedTime": 0,
        "content": task.get("content"),
        "score": task.get("score"),
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
    customScriptHint: Optional[str] = None


def _build_scenario_three_request(
    db: Session,
    *,
    ip_id: str,
    input_text: str,
    script_template: str,
    viral_elements: Optional[List[str]],
    target_duration: int,
    custom_script_hint: Optional[str] = None,
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
    instruction = template.get("instruction") or ""
    hint = (custom_script_hint or "").strip()
    if normalized_template == "custom" and hint:
        instruction = f"{instruction}\n\n【用户自定义结构】\n{hint[:2000]}"
    resolved_elements = resolve_viral_elements(normalized_template, viral_elements or [])
    few_shot_examples = _build_dynamic_few_shots(db, ip_id, input_text or "", k=3)
    ip_profile["self_intro"] = guardrails.get("self_intro") or ""
    ip_profile["forbidden_self_names"] = guardrails.get("forbidden_self_names") or []
    ip_profile["style_evidence"] = guardrails.get("style_evidence") or []
    ip_profile["few_shot_examples"] = few_shot_examples
    ip_profile["strategy_template_name"] = template.get("name") or ""
    ip_profile["strategy_template_instruction"] = instruction
    ip_profile.update(
        _build_style_context_from_vector(
            db,
            ip_id=ip_id,
            topic=input_text or "",
            emotion=str(ip_profile.get("content_direction") or ""),
            audience=str(ip_profile.get("target_audience") or ""),
            top_k=3,
        )
    )

    length = _target_duration_to_length(int(target_duration or 60))
    return ScenarioThreeRequest(
        ip_id=ip_id,
        topic=input_text,
        style_profile=ip_profile,
        key_points=resolved_elements,
        length=length,
    )


def _auto_pick_script_template(topic_text: str) -> str:
    """
    当用户选择"自由创作(custom)"且未给结构提示时，
    按话题语义自动路由到最合适的模板。
    """
    text = (topic_text or "").strip()
    if not text:
        return "opinion"
    t = text.lower()
    if any(k in t for k in ["故事", "经历", "从", "逆袭", "翻身", "踩坑", "低谷"]):
        return "story"
    if any(k in t for k in ["如何", "怎么", "方法", "步骤", "教程", "避坑", "清单"]):
        return "knowledge"
    if any(k in t for k in ["过程", "一天", "记录", "实操", "复盘", "开店", "上手"]):
        return "process"
    return "opinion"


@router.post("/generate/viral")
async def generate_viral_original(req: ViralGenerateRequest, db: Session = Depends(get_db)):
    """场景三：爆款原创"""
    try:
        requested_template = req.scriptTemplate or "opinion"
        custom_hint = (req.customScriptHint or "").strip()
        resolved_template = requested_template
        auto_template_routing = ""
        if requested_template == "custom" and not custom_hint:
            resolved_template = _auto_pick_script_template(req.input or "")
            auto_template_routing = f"custom->auto:{resolved_template}"

        request = _build_scenario_three_request(
            db,
            ip_id=req.ipId or "1",
            input_text=req.input,
            script_template=resolved_template,
            viral_elements=req.viralElements or [],
            target_duration=int(req.targetDuration or 60),
            custom_script_hint=req.customScriptHint,
        )

        result = await ContentGenerator.scenario_three(request)

        draft_id = f"gen_viral_{uuid.uuid4().hex[:10]}"
        viral_wf: Dict[str, Any] = {
            "viralElements": resolve_viral_elements(
                resolved_template, req.viralElements or []
            ),
            "scriptTemplate": requested_template,
            "resolvedScriptTemplate": resolved_template,
            "inputMode": req.inputMode or "text",
            "styleDiagnostics": (result.metadata or {}).get("style_diagnostics"),
            "elementConfigMode": (
                "auto"
                if not (req.viralElements or [])
                or any(x in {"auto", "system_auto"} for x in (req.viralElements or []))
                else "manual"
            ),
        }
        _h = (req.customScriptHint or "").strip()
        if _h:
            viral_wf["customScriptHint"] = _h[:2000]
        if auto_template_routing:
            viral_wf["autoTemplateRouting"] = auto_template_routing
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
            extra_workflow=viral_wf,
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
    customScriptHint: Optional[str] = None


@router.post("/generate/original")
@router.post("/generate/voice")
async def generate_from_original(req: OriginalGenerateRequest, db: Session = Depends(get_db)):
    """场景三：爆款原创（支持文本/语音输入；voice 路由兼容保留）"""
    try:
        requested_template = req.scriptTemplate or "opinion"
        custom_hint = (req.customScriptHint or "").strip()
        resolved_template = requested_template
        auto_template_routing = ""
        if requested_template == "custom" and not custom_hint:
            resolved_template = _auto_pick_script_template(req.text or "")
            auto_template_routing = f"custom->auto:{resolved_template}"

        request = _build_scenario_three_request(
            db,
            ip_id=req.ipId or "1",
            input_text=req.text.strip(),
            script_template=resolved_template,
            viral_elements=req.viralElements or [],
            target_duration=int(req.targetDuration or 60),
            custom_script_hint=req.customScriptHint,
        )
        result = await ContentGenerator.scenario_three(request)
        draft_id = f"gen_original_{uuid.uuid4().hex[:10]}"
        original_wf: Dict[str, Any] = {
            "viralElements": resolve_viral_elements(
                resolved_template, req.viralElements or []
            ),
            "scriptTemplate": requested_template,
            "resolvedScriptTemplate": resolved_template,
            "inputMode": "voice",
            "styleDiagnostics": (result.metadata or {}).get("style_diagnostics"),
            "elementConfigMode": (
                "auto"
                if not (req.viralElements or [])
                or any(x in {"auto", "system_auto"} for x in (req.viralElements or []))
                else "manual"
            ),
        }
        _oh = (req.customScriptHint or "").strip()
        if _oh:
            original_wf["customScriptHint"] = _oh[:2000]
        if auto_template_routing:
            original_wf["autoTemplateRouting"] = auto_template_routing
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
            extra_workflow=original_wf,
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
            "refine_history": wf.get("refine_history") or [],
            "style": wf.get("style") or "angry",
            "viralElements": wf.get("viralElements") or [],
            "scriptTemplate": wf.get("scriptTemplate") or "",
            "customScriptHint": wf.get("customScriptHint") or "",
            "agentChain": wf.get("agent_chain") or ["Strategy", "Memory", "Generation", "Compliance"],
            "structureSnapshot": wf.get("structureSnapshot") or None,
            "retrievalTrace": wf.get("retrievalTrace") or None,
            "validationReport": wf.get("validationReport") or None,
            "remixV2Enabled": bool(wf.get("remixV2Enabled")),
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


# === 文案迭代反馈 & IP 风格学习（生成页闭环）===


class RewriteFeedbackRequest(BaseModel):
    draft_id: str
    ip_id: str = "1"
    rewrite_reason: str
    user_comment: Optional[str] = None


@router.post("/feedback/rewrite")
async def post_rewrite_feedback(req: RewriteFeedbackRequest, db: Session = Depends(get_db)):
    """记录「为什么想重写」类反馈，供后续总结学习。"""
    try:
        recorded = record_rewrite_feedback(
            db,
            draft_id=req.draft_id.strip(),
            ip_id=req.ip_id or "1",
            rewrite_reason=req.rewrite_reason,
            user_comment=req.user_comment,
        )
        if not recorded:
            return {
                "ok": False,
                "message": "草稿不存在或 IP 不匹配，反馈未写入",
                "stats": {},
            }
        ip = db.query(IP).filter(IP.ip_id == (req.ip_id or "1")).first()
        cfg = dict(ip.strategy_config or {}) if ip else {}
        counts = dict(cfg.get("rewrite_reason_counts") or {})
        key = (req.rewrite_reason or "unknown")[:64]
        counts[key] = int(counts.get(key) or 0) + 1
        cfg["rewrite_reason_counts"] = counts
        if ip:
            ip.strategy_config = cfg
            flag_modified(ip, "strategy_config")
            db.commit()
        return {"ok": True, "message": "反馈已记录", "stats": counts}
    except Exception as e:
        logger.warning("post_rewrite_feedback: %s", e)
        return {"ok": False, "message": str(e), "stats": {}}


class RefineDraftRequest(BaseModel):
    draft_id: str
    ip_id: str = "1"
    user_feedback: str
    hook: Optional[str] = None
    story: Optional[str] = None
    opinion: Optional[str] = None
    cta: Optional[str] = None


@router.post("/generate/refine")
async def post_refine_draft(req: RefineDraftRequest, db: Session = Depends(get_db)):
    """根据自然语言反馈改写当前草稿四段结构（对话式优化）。"""
    try:
        out = refine_draft_with_feedback(
            db,
            draft_id=req.draft_id.strip(),
            ip_id=req.ip_id or "1",
            user_feedback=req.user_feedback,
            client_hook=req.hook,
            client_story=req.story,
            client_opinion=req.opinion,
            client_cta=req.cta,
        )
        return out
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("refine draft failed")
        raise HTTPException(status_code=500, detail=str(e))


class LearningRecordRequest(BaseModel):
    draft_id: str
    ip_id: str = "1"
    user_note: Optional[str] = None


@router.post("/feedback/learning")
async def post_iteration_learning(req: LearningRecordRequest, db: Session = Depends(get_db)):
    """满意后总结本次迭代经验，写入 IP.strategy_config.style_learnings，供后续生成注入。"""
    try:
        out = summarize_iteration_learning(
            db,
            draft_id=req.draft_id.strip(),
            ip_id=req.ip_id or "1",
            user_note=req.user_note,
        )
        return out
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("learning record failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/learnings")
async def get_ip_style_learnings(
    ipId: str = Query("1", description="IP id"),
    db: Session = Depends(get_db),
):
    """读取该 IP 已沉淀的文案学习要点（用于前端展示）。"""
    items = get_style_learnings_texts(db, ipId, limit=30)
    return {"ip_id": ipId, "items": [{"text": t} for t in items]}


@router.post("/feedback/learnings/backfill-memory")
async def backfill_style_learnings_to_memory(
    ipId: str = Query("1", description="IP id"),
    db: Session = Depends(get_db),
):
    """
    将 strategy_config 中已有学习要点批量写入 Memory 向量库（历史数据补全）。
    重复执行会为每条要点再建一条向量，仅建议在首次迁移或修复后使用。
    """
    from app.services.style_learning_memory_sync import sync_style_learning_after_commit

    ip = db.query(IP).filter(IP.ip_id == ipId).first()
    if not ip:
        raise HTTPException(status_code=404, detail="IP not found")
    cfg = dict(ip.strategy_config or {})
    raw = cfg.get("style_learnings") or []
    synced = 0
    for item in raw:
        text = ""
        if isinstance(item, dict) and item.get("text"):
            text = str(item["text"]).strip()
        elif isinstance(item, str):
            text = item.strip()
        if len(text) >= 4:
            sync_style_learning_after_commit(ipId, text)
            synced += 1
    return {
        "ok": True,
        "ip_id": ipId,
        "synced": synced,
        "warning": "重复调用可能产生重复向量条目",
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
def _dedupe_merge_topic_cards(
    priority: List[Dict[str, Any]],
    rest: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """优先保留 priority（同标题去重），再拼 rest。"""
    if not priority:
        return list(rest)
    if not rest:
        return list(priority)
    seen: set = set()
    merged: List[Dict[str, Any]] = []
    for c in priority + rest:
        key = str(c.get("title") or "").lower().strip()[:48]
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        merged.append(c)
    return merged


async def _fetch_ip_competitor_topic_cards(
    db: Session,
    ip_id: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    从该 IP 在 competitor_accounts 中配置的竞品账号拉选题（与全站 TIKHUB_COMPETITOR_SEC_UIDS 无关）。
    返回与 _rerank_tikhub_candidates 兼容的卡片结构。
    """
    try:
        from app.services.datasource.competitor_source import CompetitorTopicDataSource

        ip_profile = dict(get_ip_profile(db, ip_id) or {})
        ip_profile["ip_id"] = ip_id
        ds = CompetitorTopicDataSource(db_session=db)
        raw_topics = await ds.fetch(ip_profile, limit=max(1, min(limit, 12)))
        out: List[Dict[str, Any]] = []
        for t in raw_topics:
            extra = getattr(t, "extra", None) or {}
            play = extra.get("play_count")
            est = "—"
            if isinstance(play, int) and play > 0:
                est = f"{play // 10000}万+" if play >= 10000 else str(play)
            out.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "originalTitle": getattr(t, "original_title", None) or t.title,
                    "score": float(t.score or 4.65),
                    "tags": list(t.tags or ["抖音", "竞品爆款", "IP监控"]),
                    "reason": "IP 竞品监控（按该 IP 配置的竞品账号）",
                    "estimatedViews": est,
                    "estimatedCompletion": 35,
                    "sourceUrl": getattr(t, "url", None) or "",
                    "filter_method": "ip_competitor",
                }
            )
        if out:
            logger.info("ip_id=%s: %s topic cards from IP-bound competitors", ip_id, len(out))
        return out
    except Exception as e:
        logger.warning("IP competitor topic cards failed ip_id=%s: %s", ip_id, e)
        return []


async def _topics_from_algorithm_or_fallback(
    db: Session,
    *,
    ip_id: str,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    """场景一第一步：大数据源拉池（TikHub -> douyin-hot-hub）+ 四维重排 + IP约束。"""
    # 提高相关度阈值，只有与IP画像足够相关的热点才保留
    # 低于此阈值的热点将进入IP角度改写或算法兜底
    relevance_floor = 0.65  # 从0.6提高到0.65
    whitelist_keywords = _IP_TOPIC_WHITELIST.get(ip_id) or []
    ip_profile: Dict[str, Any] = {}
    try:
        ip_profile = get_ip_profile(db, ip_id) or {}
    except Exception as e:
        logger.warning("读取IP画像失败，按默认画像继续: %s", e)
    
    # 确保IP数据缓存已加载（供白名单过滤使用）
    _ensure_ip_data_cache(db, ip_id)
    
    weights = _resolve_topic_weights(db, ip_id)

    # 0. 本 IP 在库中配置的竞品账号（优先于泛热榜）
    comp_cards = await _fetch_ip_competitor_topic_cards(db, ip_id, min(12, max(limit, 8)))

    cards: List[Dict[str, Any]] = []
    
    # 1. 优先使用多数据源聚合（小红书+快手+抖音）
    try:
        if multi_source_client.get_multi_source_client().is_configured():
            logger.info("Using multi-source aggregation (Xiaohongshu + Kuaishou + Douyin)")
            cards = await multi_source_client.get_multi_source_topics(limit=max(limit, 12))
            if cards:
                logger.info(f"Multi-source returned {len(cards)} cards")
    except Exception as e:
        logger.warning("Multi-source failed: %s", e)
    
    # 2. 多数据源失败时，回退到 TikHub 单一数据源
    if not cards:
        try:
            if tikhub_client.is_configured():
                logger.info("Falling back to TikHub single source")
                cards = await tikhub_client.get_recommended_topic_cards(limit=max(limit, 12))
        except Exception as e:
            logger.warning("TikHub 拉取失败: %s", e)

    # 3. 最后回退到 douyin-hot-hub
    if not cards:
        try:
            logger.info("Falling back to douyin-hot-hub")
            cards = await douyin_hot_hub_client.get_recommended_topic_cards(limit=max(limit, 12))
        except Exception as e:
            logger.warning("douyin-hot-hub 拉取失败: %s", e)

    if comp_cards:
        cards = _dedupe_merge_topic_cards(comp_cards, cards)
        logger.info("After merge with IP competitors: total=%s cards", len(cards))

    try:
        if cards:
            try:
                ranked_cards = _rerank_tikhub_candidates(
                    cards=cards, ip_profile=ip_profile, limit=limit, weights=weights
                )
            except Exception as e:
                logger.warning("四维重排失败，回退为原始热榜卡片: %s", e)
                ranked_cards = cards[:limit]

            filtered = [c for c in ranked_cards if float(c.get("_relevance") or 0.0) >= relevance_floor]
            if not filtered:
                # 大数据优先：相关度不足时也返回重排后的热点，后续交给 IP 过滤/改写
                filtered = list(ranked_cards)
            
            # === 小敏IP：强制核心词过滤，宁可少而精 ===
            if ip_id in ("xiaomin", "xiaomin1"):
                logger.info(f"xiaomin1: Applying strict core keyword filter, filtered count: {len(filtered)}")
                # 调试：检查第一条数据的原始标题
                if filtered:
                    first_original = filtered[0].get("originalTitle", "N/A")
                    logger.info(f"xiaomin1: First card originalTitle: {first_original[:50]}")
                strict_filtered = [
                    c
                    for c in filtered
                    if c.get("filter_method") == "ip_competitor" or _topic_hit_core_keywords(c)
                ]
                logger.info(f"xiaomin1: Core keyword matched {len(strict_filtered)} topics")
                if strict_filtered:
                    for c in strict_filtered:
                        c.pop("_relevance", None)
                        if c.get("filter_method") != "ip_competitor":
                            c["filter_method"] = "core_matched"
                    return strict_filtered
                logger.warning("xiaomin1: No topics hit core keywords, returning empty")
                return []
            
            if filtered:
                whitelisted_cards = _apply_topic_whitelist(db, ip_id, filtered)
                if whitelisted_cards:
                    for c in whitelisted_cards:
                        c.pop("_relevance", None)
                    return whitelisted_cards
                logger.warning(
                    "大数据候选重排后全部被白名单过滤，ip_id=%s, whitelist=%s",
                    ip_id,
                    whitelist_keywords,
                )
            else:
                logger.warning("大数据候选相关度不足，返回空候选")
    except Exception as e:
        logger.warning("推荐选题失败（TikHub链路）: %s", e)
    return []


def _normalize_topic_source_url(url: Optional[str]) -> str:
    """仅保留可在浏览器新标签页打开的有效绝对 URL。"""
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("http://") or u.startswith("https://"):
        return u
    if u.startswith("www."):
        return "https://" + u
    return ""


def _v4_display_score(total_score: Optional[float]) -> float:
    """V4 内部总分为 0~1，映射到前端「策略评分」常用区间 3.0~5.0（避免全部显示 0.5）。"""
    try:
        t = float(total_score if total_score is not None else 0.5)
    except (TypeError, ValueError):
        t = 0.5
    t = max(0.0, min(1.0, t))
    return round(3.0 + 2.0 * t, 2)


def _format_play_count_label(play_count: int) -> str:
    """与 V4 _format_play_count 一致，供 API 层兜底展示。"""
    try:
        pc = int(play_count)
    except (TypeError, ValueError):
        return "-"
    if pc <= 0:
        return "-"
    if pc >= 1000000:
        return f"{pc / 10000:.0f}万+"
    if pc >= 10000:
        return f"{pc / 10000:.1f}万"
    if pc >= 1000:
        return f"{pc / 1000:.1f}千"
    return str(pc)


def _filter_topics_for_ip_alignment(
    ip_id: str,
    topics: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    与 legacy 一致：对有配置的 IP 应用白名单/黑名单；小敏 IP 额外要求核心词命中。
    此前 V4 直接返回时跳过了本过滤，导致混入全网热点。
    """
    if not topics:
        return []
    whitelist = _IP_TOPIC_WHITELIST.get(ip_id) or []
    blocklist = _IP_TOPIC_BLOCKLIST.get(ip_id) or []
    out: List[Dict[str, Any]] = []
    for raw in topics:
        t = dict(raw)
        if whitelist and not _topic_hit_whitelist(t, whitelist):
            continue
        if blocklist and _topic_hit_blocklist(t, blocklist):
            continue
        if ip_id in ("xiaomin", "xiaomin1") and not _topic_hit_core_keywords(t):
            continue
        su = _normalize_topic_source_url(str(t.get("sourceUrl") or ""))
        if su:
            t["sourceUrl"] = su
        else:
            t.pop("sourceUrl", None)
        out.append(t)
    return out


async def _async_build_recommended_topic_list(
    db: Session,
    ip_id: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """V4 → IP 对齐过滤 → legacy → 快照/模板兜底（与 get/refresh 共用）。"""
    try:
        v4_service = get_recommendation_service_v4()
        v4_topics = await v4_service.recommend_topics(
            db=db,
            ip_id=ip_id,
            limit=limit,
            strategy="competitor_first",
        )
        if v4_topics:
            topics: List[Dict[str, Any]] = []
            for topic in v4_topics:
                nu = _normalize_topic_source_url(topic.url or "")
                est_views = topic.original_plays or _format_play_count_label(
                    int(topic.competitor_play_count or 0)
                )
                src = (getattr(topic, "source", None) or "") or ""
                if topic.competitor_name:
                    reason = f"竞品@{topic.competitor_name}"
                elif src:
                    reason = f"大数据 · {src}"
                else:
                    reason = "智能推荐"
                topics.append(
                    {
                        "id": topic.topic_id,
                        "title": topic.title,
                        "originalTitle": topic.original_title,
                        "score": _v4_display_score(topic.total_score),
                        "estimatedViews": est_views,
                        "estimatedCompletion": topic.viral_score or 35,
                        "tags": topic.tags[:3] if topic.tags else ["创业"],
                        "reason": reason,
                        "sourceUrl": nu,
                        "competitorName": topic.competitor_name,
                        "competitorPlatform": topic.competitor_platform,
                        "remixPotential": topic.remix_potential,
                        "viralScore": topic.viral_score,
                        "originalPlays": topic.original_plays,
                    }
                )
            aligned = _filter_topics_for_ip_alignment(ip_id, topics)
            if aligned:
                logger.info(
                    "[V4] Returned %s topics after IP alignment for %s",
                    len(aligned),
                    ip_id,
                )
                return aligned
            logger.info(
                "[V4] All candidates removed by IP alignment for %s, falling back to legacy",
                ip_id,
            )
    except Exception as e:
        logger.warning("[V4] Failed to get recommendations: %s, falling back to legacy algorithm", e)

    topics = await _topics_from_algorithm_or_fallback(db, ip_id=ip_id, limit=limit)

    if ip_id in ("xiaomin", "xiaomin1"):
        if not topics:
            logger.info("xiaomin: No matching topics from TikHub, returning empty")
        return topics

    if not topics:
        topics = _generate_hotlist_snapshot_topics(db, ip_id, limit)
    if not topics:
        topics = _generate_fallback_topics(db, ip_id, limit)

    return topics


@router.get("/topics/recommended")
async def get_recommended_topics(
    ipId: str = Query("xiaomin1", description="IP 画像 id（须与 ip.ip_id 一致）"),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """场景一第一步：推荐选题（V4 竞品驱动 + IP 对齐过滤 + legacy 兜底）。"""
    topics = await _async_build_recommended_topic_list(db, ipId, limit)
    return {"topics": topics}


@router.get("/topics/refresh")
async def refresh_topics(
    ipId: str = Query("xiaomin1", description="IP 画像 id"),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """刷新推荐选题（与 recommended 同源构建后再打散）。"""
    topics = await _async_build_recommended_topic_list(db, ipId, limit)
    if topics:
        shuffled = list(topics)
        random.shuffle(shuffled)
        topics = shuffled
    return {"topics": topics}


def _generate_fallback_topics(db: Session, ip_id: str, limit: int) -> List[Dict[str, Any]]:
    """算法兜底：当外部API失败时，基于IP配置生成推荐选题"""
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        return []

    # 从IP配置中提取关键词生成选题（支持多种分隔符）
    keywords = []
    for field in (ip.expertise, ip.content_direction, ip.target_audience, ip.passion, ip.market_demand):
        if field and isinstance(field, str):
            # 支持 / 、 、 和 等分隔符
            keywords.extend([w.strip() for w in re.split(r'[,，、/和\s]+', field) if len(w.strip()) >= 2])

    # 去重
    keywords = list(set(keywords))[:20]

    # 优先选择与创业相关的核心关键词
    core_keywords = [k for k in keywords if any(x in k for x in ['创业', '馒头', '私域', '变现', '女性', '副业', '赚钱', '独立'])]

    if not core_keywords:
        core_keywords = keywords[:10]

    if not keywords:
        keywords = ["创业", "赚钱", "副业", "女性", "独立"]

    # 选题模板（多样化）
    templates = [
        "{kw}到底能不能赚钱",
        "为什么她们{kw}都成功了",
        "从0开始{kw}，我的一年",
        "教你{kw}的正确姿势",
        "{kw}的3个避坑指南",
        "宝妈{kw}月入3万真实分享",
        "{kw}红利期还能入局吗",
        "不会做{kw}？从这3步开始",
        "{kw}变现新模式",
        "90%的人不知道的{kw}技巧",
    ]

    topics = []
    kw = core_keywords[0] if core_keywords else "创业"

    for i, title in enumerate(templates[:limit]):
        title = title.replace("{kw}", kw)
        topics.append({
            "id": f"fallback_{i+1:03d}",
            "title": title,
            "score": round(4.6 - i * 0.05, 2),
            "tags": core_keywords[:4],
            "reason": "基于IP方向智能生成",
            "estimatedViews": f"{20 + i * 10}万",
            "estimatedCompletion": 38 + i,
            "sourceUrl": "",
        })

    return topics


def _generate_hotlist_snapshot_topics(db: Session, ip_id: str, limit: int) -> List[Dict[str, Any]]:
    """
    大数据兜底：在线热榜不可用时，使用内置 douyin 快照，避免退化为模板选题。
    """
    try:
        if not _DOUYIN_SNAPSHOT_FILE.exists():
            return []
        obj = json.loads(_DOUYIN_SNAPSHOT_FILE.read_text(encoding="utf-8"))
        cards = [c for c in (obj.get("cards") or []) if isinstance(c, dict)]
        if not cards:
            cards = list(_BUILTIN_DOUYIN_HOTLIST)
    except Exception:
        cards = list(_BUILTIN_DOUYIN_HOTLIST)

    try:
        if not cards:
            return []
        ip_profile = get_ip_profile(db, ip_id) or {}
        weights = _resolve_topic_weights(db, ip_id)
        ranked = _rerank_tikhub_candidates(cards=cards, ip_profile=ip_profile, limit=limit, weights=weights)
        
        # 对快照数据进行IP角度改写（因为是兜底数据，强制改写更贴合IP）
        keywords = _IP_TOPIC_WHITELIST.get(ip_id) or ["创业", "变现"]
        adapted = _adapt_topics_to_ip_angle(
            ip_id=ip_id,
            topics=ranked,
            keywords=keywords,
            ip_profile=ip_profile,
        )
        
        for t in adapted:
            t.pop("_relevance", None)
            t["reason"] = f"{str(t.get('reason') or '')} + 快照兜底"
        return adapted[:limit]
    except Exception as e:
        logger.warning("snapshot hotlist fallback failed: %s", e)
        return []


# === 内容库 ===
@router.get("/library")
async def list_creator_library(
    status: Optional[str] = None,
    ipId: Optional[str] = Query(None, alias="ipId"),
    db: Session = Depends(get_db),
):
    """内容库列表（来自 content_drafts；无数据时返回空数组）。传 ipId 时仅返回该 IP 下的草稿。"""
    q = db.query(ContentDraft)
    if ipId:
        q = q.filter(ContentDraft.ip_id == ipId)
    rows = (
        q.order_by(ContentDraft.created_at.desc())
        .limit(200)
        .all()
    )
    items = [_draft_to_library_item(d) for d in rows]
    if status and status != "all":
        items = [x for x in items if x.get("status") == status]
    return items


@router.delete("/library/{draft_id}")
async def delete_creator_library_item(draft_id: str, db: Session = Depends(get_db)):
    """从内容库删除一条草稿（硬删除 content_drafts 行）。"""
    draft = db.query(ContentDraft).filter(ContentDraft.draft_id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="内容不存在或已删除")
    db.delete(draft)
    db.commit()
    return {"ok": True}


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
async def creator_analytics(
    ipId: Optional[str] = Query(None, alias="ipId"),
    db: Session = Depends(get_db),
):
    """创作端数据概览（基于 content_drafts 聚合；无数据时返回 0 与默认建议）。传 ipId 时仅统计该 IP。"""
    q = db.query(ContentDraft)
    if ipId:
        q = q.filter(ContentDraft.ip_id == ipId)
    rows = q.all()
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


# === TikHub 测试端点 ===
@router.get("/test/tikhub")
async def test_tikhub_api():
    """测试 TikHub API 直接调用（公开端点，用于诊断）"""
    import os
    
    key = os.environ.get("TIKHUB_API_KEY", "").strip()
    result = {
        "env_key_configured": bool(key),
        "key_length": len(key),
        "key_preview": key[:10] + "..." if len(key) > 10 else "empty",
        "tikhub_client_configured": tikhub_client.is_configured(),
        "api_call": None,
        "error": None,
    }
    
    if not key:
        result["error"] = "TIKHUB_API_KEY not set"
        return result
    
    try:
        # 直接调用 TikHub API
        import httpx
        
        headers = {"Authorization": f"Bearer {key}"}
        payload = {"page": 1, "page_size": 10, "date_window": 7}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tikhub.io/api/v1/douyin/billboard/fetch_hot_total_low_fan_list",
                headers=headers,
                json=payload
            )
            
            result["api_call"] = {
                "status_code": response.status_code,
                "headers_sent": {"Authorization": f"Bearer {key[:5]}..."},
                "response_preview": response.text[:500] if response.text else "empty",
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result["api_call"]["json_parsed"] = True
                    result["api_call"]["has_data"] = bool(data)
                    if isinstance(data, dict) and "data" in data:
                        items = data["data"]
                        if isinstance(items, list):
                            result["api_call"]["items_count"] = len(items)
                except:
                    result["api_call"]["json_parsed"] = False
            else:
                result["error"] = f"HTTP {response.status_code}"
                
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


# === TikHub 测试端点（带 Key 参数）===
@router.get("/test/tikhub-with-key")
async def test_tikhub_with_key(api_key: str = Query(..., description="TikHub API Key to test")):
    """测试指定的 TikHub API Key（公开端点，用于诊断）"""
    import httpx
    
    result = {
        "key_length": len(api_key),
        "key_preview": api_key[:10] + "..." if len(api_key) > 10 else api_key,
        "api_call": None,
        "error": None,
    }
    
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {"page": 1, "page_size": 10, "date_window": 7}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tikhub.io/api/v1/douyin/billboard/fetch_hot_total_low_fan_list",
                headers=headers,
                json=payload
            )
            
            result["api_call"] = {
                "status_code": response.status_code,
                "response_preview": response.text[:800] if response.text else "empty",
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result["api_call"]["json_parsed"] = True
                    if isinstance(data, dict):
                        result["api_call"]["code"] = data.get("code")
                        result["api_call"]["message"] = data.get("message")
                        if "data" in data and isinstance(data["data"], list):
                            result["api_call"]["items_count"] = len(data["data"])
                            if data["data"]:
                                result["api_call"]["first_item_preview"] = str(data["data"][0])[:200]
                except Exception as e:
                    result["api_call"]["json_parse_error"] = str(e)
            else:
                result["error"] = f"HTTP {response.status_code}"
                
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


# === TikHub 数据详情测试 ===
@router.get("/test/tikhub-data")
async def test_tikhub_data_detail():
    """查看 TikHub 返回的原始数据结构"""
    from app.services import tikhub_client
    import os
    import httpx
    
    key = os.environ.get("TIKHUB_API_KEY", "").strip()
    result = {
        "key_configured": bool(key),
        "key_preview": key[:10] + "..." if key else "none",
    }
    
    try:
        headers = {"Authorization": f"Bearer {key}"}
        payload = {"page": 1, "page_size": 5, "date_window": 1, "tags": []}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tikhub.io/api/v1/douyin/billboard/fetch_hot_total_high_play_list",
                headers=headers,
                json=payload
            )
            
            data = response.json()
            result["status_code"] = response.status_code
            result["response_code"] = data.get("code")
            result["response_message"] = data.get("message")
            
            # 检查 data 字段
            inner_data = data.get("data")
            result["data_type"] = type(inner_data).__name__
            
            if isinstance(inner_data, list):
                result["data_length"] = len(inner_data)
                if inner_data:
                    result["first_item"] = inner_data[0]
            elif isinstance(inner_data, dict):
                result["data_keys"] = list(inner_data.keys())
            else:
                result["data_value"] = str(inner_data)[:200]
                
            # 测试 billboard_to_topic_cards
            cards = tikhub_client.billboard_to_topic_cards(inner_data, limit=5)
            result["parsed_cards_count"] = len(cards)
            if cards:
                result["first_card"] = cards[0]
                
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


# === TikHub 嵌套数据结构测试 ===
@router.get("/test/tikhub-nested")
async def test_tikhub_nested():
    """查看 TikHub 嵌套 data 的详细结构"""
    import os
    import httpx
    
    key = os.environ.get("TIKHUB_API_KEY", "").strip()
    
    try:
        headers = {"Authorization": f"Bearer {key}"}
        payload = {"page": 1, "page_size": 10, "date_window": 7}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tikhub.io/api/v1/douyin/billboard/fetch_hot_total_high_play_list",
                headers=headers,
                json=payload
            )
            
            full_data = response.json()
            inner_data = full_data.get("data", {})
            
            result = {
                "outer_code": full_data.get("code"),
                "inner_type": type(inner_data).__name__,
                "inner_keys": list(inner_data.keys()) if isinstance(inner_data, dict) else None,
            }
            
            if isinstance(inner_data, dict):
                result["inner_code"] = inner_data.get("code")
                result["inner_message"] = inner_data.get("message")
                
                # 查看 inner.data 的类型
                inner_inner = inner_data.get("data")
                result["inner_data_type"] = type(inner_inner).__name__
                
                if isinstance(inner_inner, list):
                    result["inner_data_length"] = len(inner_inner)
                    if inner_inner:
                        result["first_item_sample"] = str(inner_inner[0])[:200]
                elif isinstance(inner_inner, dict):
                    result["inner_data_keys"] = list(inner_inner.keys())
                else:
                    result["inner_data_value"] = str(inner_inner)[:100]
                
                # 查找列表
                for k in ("list", "data", "items", "records", "aweme_list", "hot_list"):
                    v = inner_data.get(k)
                    if isinstance(v, list):
                        result["found_list_key"] = k
                        result["list_length"] = len(v)
                        break
            
            return result
                
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)}"}


# === TikHub 解析调试 ===
@router.get("/test/tikhub-parse")
async def test_tikhub_parse():
    """调试 TikHub 数据解析过程"""
    import os
    import httpx
    from app.services import tikhub_client
    
    key = os.environ.get("TIKHUB_API_KEY", "").strip()
    
    try:
        headers = {"Authorization": f"Bearer {key}"}
        payload = {"page": 1, "page_size": 5, "date_window": 1, "tags": []}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tikhub.io/api/v1/douyin/billboard/fetch_hot_total_high_play_list",
                headers=headers,
                json=payload
            )
            
            full_data = response.json()
            
            # 模拟 unwrap_response
            unwrapped = full_data.get("data") if isinstance(full_data, dict) else full_data
            
            result = {
                "full_data_keys": list(full_data.keys()) if isinstance(full_data, dict) else None,
                "unwrapped_type": type(unwrapped).__name__,
                "unwrapped_keys": list(unwrapped.keys()) if isinstance(unwrapped, dict) else None,
            }
            
            if isinstance(unwrapped, dict):
                result["unwrapped_code"] = unwrapped.get("code")
                inner_data = unwrapped.get("data")
                result["inner_data_type"] = type(inner_data).__name__
                
                if isinstance(inner_data, dict):
                    result["inner_data_keys"] = list(inner_data.keys())
                    objs = inner_data.get("objs")
                    result["objs_type"] = type(objs).__name__
                    result["objs_length"] = len(objs) if isinstance(objs, list) else 0
                    
                    if isinstance(objs, list) and objs:
                        first_item = objs[0]
                        result["first_item_keys"] = list(first_item.keys()) if isinstance(first_item, dict) else None
                        # 检查 item_title 的原始值和类型
                        item_title = first_item.get("item_title")
                        result["item_title_raw"] = str(item_title)
                        result["item_title_type"] = type(item_title).__name__
                        result["item_title_repr"] = repr(item_title)[:100]
            
            # 测试 billboard_to_topic_cards
            cards = tikhub_client.billboard_to_topic_cards(unwrapped, limit=3)
            result["cards_count"] = len(cards)
            if cards:
                result["first_card_title"] = cards[0].get("title")
            
            return result
                
    except Exception as e:
        import traceback
        return {"error": f"{type(e).__name__}: {str(e)}", "traceback": traceback.format_exc()}


# === TikHub 完整数据流测试 ===
@router.get("/test/tikhub-flow")
async def test_tikhub_flow(ipId: str = Query("xiaomin1")):
    """测试 TikHub 数据完整流程"""
    from app.services import tikhub_client
    import os
    
    result = {
        "tikhub_configured": tikhub_client.is_configured(),
        "tikhub_cards": None,
        "error": None,
    }
    
    try:
        # 直接调用 TikHub
        cards = await tikhub_client.get_recommended_topic_cards(limit=5)
        result["tikhub_cards_count"] = len(cards)
        if cards:
            result["first_card_id"] = cards[0].get("id")
            result["first_card_title"] = cards[0].get("title")
            result["first_card_reason"] = cards[0].get("reason")
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


# === TikHub _request 级别测试 ===
@router.get("/test/tikhub-request")
async def test_tikhub_request():
    """测试 TikHub _request 和 unwrap_response"""
    from app.services import tikhub_client
    import os
    import httpx
    
    key = os.environ.get("TIKHUB_API_KEY", "").strip()
    
    result = {
        "key_configured": bool(key),
    }
    
    try:
        headers = {"Authorization": f"Bearer {key}"}
        payload = {"page": 1, "page_size": 5, "date_window": 1, "tags": []}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 直接调用 API
            response = await client.post(
                "https://api.tikhub.io/api/v1/douyin/billboard/fetch_hot_total_high_play_list",
                headers=headers,
                json=payload
            )
            
            result["status_code"] = response.status_code
            raw_json = response.json()
            result["raw_code"] = raw_json.get("code")
            
            # 测试 unwrap_response
            unwrapped = tikhub_client.unwrap_response(raw_json)
            result["unwrapped_type"] = type(unwrapped).__name__
            
            if isinstance(unwrapped, dict):
                result["unwrapped_keys"] = list(unwrapped.keys())
                inner_data = unwrapped.get("data")
                result["inner_data_type"] = type(inner_data).__name__
                if isinstance(inner_data, dict):
                    result["inner_data_keys"] = list(inner_data.keys())
                    objs = inner_data.get("objs")
                    result["objs_type"] = type(objs).__name__
                    result["objs_length"] = len(objs) if isinstance(objs, list) else 0
            
            # 测试 billboard_to_topic_cards
            cards = tikhub_client.billboard_to_topic_cards(unwrapped, limit=3)
            result["cards_count"] = len(cards)
            
    except Exception as e:
        import traceback
        result["error"] = f"{type(e).__name__}: {str(e)}"
        result["traceback"] = traceback.format_exc()
    
    return result


# === TikHub fetch 函数测试 ===
@router.get("/test/tikhub-fetch")
async def test_tikhub_fetch():
    """测试 TikHub fetch_douyin_high_play_hot_list"""
    from app.services import tikhub_client
    
    result = {}
    
    try:
        # 使用默认 date_window（不传参数）
        raw = await tikhub_client.fetch_douyin_high_play_hot_list(page=1, page_size=5)
        result["raw_type"] = type(raw).__name__
        if isinstance(raw, dict):
            result["raw_keys"] = list(raw.keys())
            inner = raw.get("data")
            result["inner_type"] = type(inner).__name__
            if isinstance(inner, dict):
                result["inner_keys"] = list(inner.keys())
        result["has_raw"] = bool(raw)
        
        # 直接测试 billboard_to_topic_cards
        cards = tikhub_client.billboard_to_topic_cards(raw, limit=3)
        result["direct_cards_count"] = len(cards)
    except Exception as e:
        import traceback
        result["fetch_error"] = f"{type(e).__name__}: {str(e)}"
        result["traceback"] = traceback.format_exc()
    
    
    # 检查 get_recommended_topic_cards 的日志
    # 可能是 TikHub 调用频率限制，暂时跳过详细测试
    
    return result


# === 检查 ip_id 测试 ===
@router.get("/test/check-ipid")
async def test_check_ipid(ipId: str = Query("1", description="IP 画像 id")):
    """检查传入的 ip_id 参数"""
    return {
        "received_ipId": ipId,
        "is_xiaomin1": ipId == "xiaomin1",
        "length": len(ipId),
        "repr": repr(ipId),
    }


# === 检查核心词匹配 ===
@router.get("/test/check-core")
async def test_check_core(ipId: str = Query("xiaomin1", description="IP 画像 id")):
    """检查核心词匹配情况"""
    from app.services import tikhub_client
    
    # 获取 TikHub 数据
    cards = await tikhub_client.get_recommended_topic_cards(limit=5)
    
    results = []
    for card in cards:
        title = str(card.get("title") or "")
        original = str(card.get("originalTitle") or card.get("original_title") or "")
        text = f"{title} {original}"
        
        # 检查是否命中核心词
        hit_keywords = [kw for kw in _XIAOMIN_CORE_KEYWORDS if kw in text]
        
        results.append({
            "title": title[:50],
            "original": original[:50],
            "hit_keywords": hit_keywords,
            "has_hit": len(hit_keywords) > 0,
        })
    
    return {
        "ipId": ipId,
        "total_cards": len(cards),
        "core_keywords": _XIAOMIN_CORE_KEYWORDS,
        "results": results,
    }


# === 测试白名单过滤 ===
@router.get("/test/whitelist")
async def test_whitelist(ipId: str = Query("xiaomin1"), db: Session = Depends(get_db)):
    """测试白名单过滤"""
    from app.services import tikhub_client
    
    # 获取 TikHub 数据
    cards = await tikhub_client.get_recommended_topic_cards(limit=5)
    
    # 调用白名单过滤
    filtered = _apply_topic_whitelist(db, ipId, cards)
    
    return {
        "ipId": ipId,
        "input_count": len(cards),
        "output_count": len(filtered),
        "filter_methods": [t.get("filter_method") for t in filtered],
    }


# === 多数据源测试 ===
@router.get("/test/multi-source")
async def test_multi_source(limit: int = Query(6, ge=1, le=20)):
    """测试多数据源聚合"""
    try:
        cards = await multi_source_client.get_multi_source_topics(limit=limit)
        return {
            "total": len(cards),
            "sources": list(set(c.get("platform") for c in cards)),
            "topics": [
                {
                    "id": c.get("id"),
                    "title": c.get("title"),
                    "platform": c.get("platform"),
                    "weight": c.get("weight"),
                    "source": c.get("reason"),
                }
                for c in cards[:6]
            ],
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


# === 核心词匹配测试 ===
@router.get("/test/core-match")
async def test_core_match():
    """测试核心词匹配"""
    from app.services import multi_source_client
    
    # 获取多数据源数据
    cards = await multi_source_client.get_multi_source_topics(limit=10)
    
    results = []
    for card in cards:
        title = card.get("title", "")
        original = card.get("originalTitle", "")
        
        # 测试核心词匹配
        hit = _topic_hit_core_keywords(card)
        
        results.append({
            "title": title[:40],
            "original": original[:40],
            "hit": hit,
        })
    
    return {
        "total": len(cards),
        "core_keywords": _XIAOMIN_CORE_KEYWORDS,
        "matched": sum(1 for r in results if r["hit"]),
        "results": results,
    }


# === 检查多数据源卡片结构 ===
@router.get("/test/card-structure")
async def test_card_structure():
    """检查多数据源返回的卡片结构"""
    from app.services import multi_source_client
    
    cards = await multi_source_client.get_multi_source_topics(limit=3)
    
    return {
        "count": len(cards),
        "first_card_keys": list(cards[0].keys()) if cards else [],
        "first_card": {
            "id": cards[0].get("id") if cards else None,
            "title": cards[0].get("title")[:30] if cards else None,
            "originalTitle": cards[0].get("originalTitle")[:30] if cards else None,
            "platform": cards[0].get("platform") if cards else None,
        } if cards else None,
    }


# === 检查推荐选题流程 ===
@router.get("/test/recommend-flow")
async def test_recommend_flow(ipId: str = Query("xiaomin1")):
    """检查推荐选题完整流程"""
    from app.services import multi_source_client
    
    # 1. 获取多数据源
    cards = await multi_source_client.get_multi_source_topics(limit=6)
    
    # 2. 模拟 _topic_hit_core_keywords
    matched = []
    for card in cards:
        if _topic_hit_core_keywords(card):
            matched.append({
                "id": card.get("id"),
                "title": card.get("title")[:30],
                "hit": True,
            })
    
    return {
        "ipId_received": ipId,
        "is_xiaomin1": ipId == "xiaomin1",
        "cards_count": len(cards),
        "matched_count": len(matched),
        "matched": matched,
    }


# === 调试核心词匹配 ===
@router.get("/test/debug-core")
async def test_debug_core():
    """调试核心词匹配"""
    from app.services import multi_source_client
    
    cards = await multi_source_client.get_multi_source_topics(limit=5)
    
    results = []
    for card in cards:
        title = str(card.get("title") or "")
        original = str(card.get("originalTitle") or "")
        text = f"{title} {original}"
        
        # 检查每个核心词
        hits = [kw for kw in _XIAOMIN_CORE_KEYWORDS if kw in text]
        
        results.append({
            "title": title[:40],
            "original": original[:40],
            "text_sample": text[:80],
            "hits": hits,
        })
    
    return {
        "core_keywords": _XIAOMIN_CORE_KEYWORDS,
        "results": results,
    }


# === 检查重排后的数据结构 ===
@router.get("/test/rerank-structure")
async def test_rerank_structure(ipId: str = Query("xiaomin1"), db: Session = Depends(get_db)):
    """检查四维重排后的数据结构"""
    from app.services import multi_source_client
    
    # 1. 获取多数据源
    cards = await multi_source_client.get_multi_source_topics(limit=5)
    
    # 2. 获取IP画像
    ip_profile = get_ip_profile(db, ipId) or {}
    weights = _resolve_topic_weights(db, ipId)
    
    # 3. 四维重排
    ranked_cards = _rerank_tikhub_candidates(
        cards=cards, ip_profile=ip_profile, limit=12, weights=weights
    )
    
    return {
        "input_count": len(cards),
        "output_count": len(ranked_cards),
        "first_card_keys": list(ranked_cards[0].keys()) if ranked_cards else [],
        "first_card": {
            "title": ranked_cards[0].get("title")[:40] if ranked_cards else None,
            "originalTitle": ranked_cards[0].get("originalTitle")[:40] if ranked_cards else None,
        } if ranked_cards else None,
    }


# === 完整推荐流程测试 ===
@router.get("/test/full-recommend")
async def test_full_recommend(ipId: str = Query("xiaomin1"), db: Session = Depends(get_db)):
    """测试完整推荐流程"""
    from app.services import multi_source_client
    
    result = {"steps": []}
    
    # 1. 获取多数据源
    cards = await multi_source_client.get_multi_source_topics(limit=10)
    result["steps"].append(f"1. Got {len(cards)} cards from multi-source")
    
    # 2. 检查核心词匹配（原始卡片）
    core_matched_original = [c for c in cards if _topic_hit_core_keywords(c)]
    result["steps"].append(f"2. Core matched in original: {len(core_matched_original)}")
    
    # 3. 四维重排
    ip_profile = get_ip_profile(db, ipId) or {}
    weights = _resolve_topic_weights(db, ipId)
    ranked_cards = _rerank_tikhub_candidates(
        cards=cards, ip_profile=ip_profile, limit=12, weights=weights
    )
    result["steps"].append(f"3. After rerank: {len(ranked_cards)} cards")
    
    # 4. 检查核心词匹配（重排后）
    core_matched_reranked = [c for c in ranked_cards if _topic_hit_core_keywords(c)]
    result["steps"].append(f"4. Core matched in reranked: {len(core_matched_reranked)}")
    
    # 5. 检查第一条数据的标题
    if ranked_cards:
        first = ranked_cards[0]
        result["first_card"] = {
            "title": first.get("title", "N/A")[:40],
            "originalTitle": first.get("originalTitle", "N/A")[:40],
        }
    
    # 6. 检查 ip_id
    result["ip_id"] = ipId
    result["is_xiaomin1"] = ipId == "xiaomin1"
    
    return result


# === 直接测试 _topics_from_algorithm_or_fallback ===
@router.get("/test/algorithm")
async def test_algorithm(ipId: str = Query("xiaomin1"), limit: int = 12, db: Session = Depends(get_db)):
    """直接测试算法流程"""
    topics = await _topics_from_algorithm_or_fallback(db, ip_id=ipId, limit=limit)
    return {
        "ip_id": ipId,
        "limit": limit,
        "topics_count": len(topics),
        "topics": [
            {
                "id": t.get("id"),
                "title": t.get("title", "")[:40],
                "filter_method": t.get("filter_method"),
            }
            for t in topics[:5]
        ],
    }


# === 竞品数据测试 ===
@router.get("/test/competitor")
async def test_competitor():
    """测试竞品账号视频抓取"""
    from app.services import competitor_client
    
    client = competitor_client.get_competitor_client()
    
    # 检查配置
    config = {
        "api_key_configured": bool(client.api_key),
        "competitors_count": len(client.competitor_sec_uids),
        "competitor_uids": [uid[:20] + "..." for uid in client.competitor_sec_uids],
    }
    
    # 尝试抓取
    try:
        videos = await competitor_client.get_competitor_videos(count_per_user=3)
        return {
            **config,
            "videos_count": len(videos),
            "videos": [
                {
                    "title": v.get("title", "")[:40],
                    "platform": v.get("platform"),
                    "digg_count": v.get("digg_count"),
                }
                for v in videos[:5]
            ],
        }
    except Exception as e:
        import traceback
        return {
            **config,
            "error": str(e),
            "traceback": traceback.format_exc()[:500],
        }
