"""
Creator API Router
对接前端 /api/creator/* 路由
"""

from datetime import datetime, timezone
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
    ScenarioTwoRequest,
    ScenarioThreeRequest,
)
from app.services import remix_recommendation_service, tikhub_client, douyin_hot_hub_client
from app.services.semantic_topic_filter import filter_topics_by_similarity
from app.services.style_corpus_service import StyleCorpusService
from app.services.strategy_config_service import get_merged_config

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
                "estimatedViews": str(card.get("estimatedViews") or "-"),
                "estimatedCompletion": int(card.get("estimatedCompletion") or 0),
                "sourceUrl": str(card.get("sourceUrl") or ""),
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
    
    # 针对小敏IP的特殊处理
    is_xiaomin = ip_id == "xiaomin1"
    
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

    # 都没有匹配：执行「热点 x IP」角度改写，确保仍返回大数据热点
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
        ip_profile["ip_id"] = req.ipId or "1"

        competitor_text = req.url.strip()[:8000]
        if tikhub_client.is_configured():
            competitor_text = await tikhub_client.extract_competitor_text_for_remix(req.url.strip())
        ip_profile.update(
            _build_style_context_from_vector(
                db,
                ip_id=req.ipId or "1",
                topic=(competitor_text or req.url or "")[:200],
                emotion=str(ip_profile.get("content_direction") or ""),
                audience=str(ip_profile.get("target_audience") or ""),
                top_k=3,
            )
        )

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
            extra_workflow={
                "source_url": req.url,
                "styleDiagnostics": (result.metadata or {}).get("style_diagnostics"),
                "structureSnapshot": (result.metadata or {}).get("structure_snapshot"),
                "retrievalTrace": (result.metadata or {}).get("retrieval_trace"),
                "validationReport": (result.metadata or {}).get("validation_report"),
                "remixV2Enabled": (result.metadata or {}).get("remix_v2_enabled"),
            },
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

    cards: List[Dict[str, Any]] = []
    try:
        if tikhub_client.is_configured():
            cards = await tikhub_client.get_recommended_topic_cards(limit=max(limit, 12))
    except Exception as e:
        logger.warning("TikHub 拉取失败，切换到 douyin-hot-hub: %s", e)

    if not cards:
        try:
            cards = await douyin_hot_hub_client.get_recommended_topic_cards(limit=max(limit, 12))
        except Exception as e:
            logger.warning("douyin-hot-hub 拉取失败: %s", e)

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


@router.get("/topics/recommended")
async def get_recommended_topics(
    ipId: str = Query("1", description="IP 画像 id"),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """场景一第一步：推荐选题（四维评分；不生成正文）。"""
    topics = await _topics_from_algorithm_or_fallback(db, ip_id=ipId, limit=limit)

    # 如果外部API都失败，使用算法兜底生成选题
    if not topics:
        topics = _generate_hotlist_snapshot_topics(db, ipId, limit)
    if not topics:
        topics = _generate_fallback_topics(db, ipId, limit)

    return {"topics": topics}


@router.get("/topics/refresh")
async def refresh_topics(
    ipId: str = Query("1", description="IP 画像 id"),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """刷新推荐选题（四维评分推荐后打散）。"""
    topics = await _topics_from_algorithm_or_fallback(db, ip_id=ipId, limit=limit)

    # 如果外部API都失败，使用算法兜底
    if not topics:
        topics = _generate_hotlist_snapshot_topics(db, ipId, limit)
    if not topics:
        topics = _generate_fallback_topics(db, ipId, limit)
    else:
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
        payload = {"page": 1, "page_size": 3, "date_window": 1, "tags": []}
        
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
        payload = {"page": 1, "page_size": 3, "date_window": 1, "tags": []}
        
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
        payload = {"page": 1, "page_size": 3, "date_window": 1, "tags": []}
        
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
        raw = await tikhub_client.fetch_douyin_high_play_hot_list(page=1, page_size=5, date_window=1)
        result["raw_type"] = type(raw).__name__
        if isinstance(raw, dict):
            result["raw_keys"] = list(raw.keys())
        result["has_raw"] = bool(raw)
    except Exception as e:
        result["fetch_error"] = f"{type(e).__name__}: {str(e)}"
    
    try:
        cards = await tikhub_client.get_recommended_topic_cards(limit=5)
        result["cards_count"] = len(cards)
    except Exception as e:
        result["get_cards_error"] = f"{type(e).__name__}: {str(e)}"
    
    return result
