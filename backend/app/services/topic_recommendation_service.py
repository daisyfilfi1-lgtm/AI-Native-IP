"""
智能选题推荐服务 - TIKHUB优先 + 算法兜底
"""
import os
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP
from app.services.strategy_config_service import get_merged_config


# ==================== 评分维度定义 ====================

@dataclass
class TopicScore:
    """选题评分结果"""
    topic: str
    url: str
    platform: str
    
    # 四维评分 (0-100)
    traffic_score: float      # 流量潜力
    monetization_score: float # 变现关联
    fit_score: float          # IP契合度
    cost_score: float         # 制作成本
    
    # 综合评分
    overall_score: float
    total_score: int          # 评分卡总分
    
    # 详细信息
    likes: int = 0
    comments: int = 0
    shares: int = 0
    author_followers: int = 0
    viral_elements: List[str] = None
    
    # 数据来源
    source: str = "tikhub"  # tikhub or algorithm
    
    def __post_init__(self):
        if self.viral_elements is None:
            self.viral_elements = []


# ==================== 爆款元素识别 ====================

VIRAL_ELEMENTS = {
    "cost": ["省钱", "免费", "便宜", "划算", "性价比"],
    "crowd": ["大家", "很多人", "都在", "你身边", "同龄人"],
    "weird": ["奇怪", "没想到", "居然", "竟然", "颠覆", "反直觉"],
    "worst": ["最差", "踩坑", "后悔", "避坑", "教训"],
    "contrast": ["但是", "然而", "其实", "原来", "对比"],
    "nostalgia": ["以前", "当年", "回忆", "曾经"],
    "hormone": ["激动", "兴奋", "爽", "燃", "破防"],
    "top": ["第一", "最强", "顶级", "天花板", "必看"],
}


def detect_viral_elements(text: str) -> List[str]:
    found = []
    text_lower = text.lower()
    for element, keywords in VIRAL_ELEMENTS.items():
        for kw in keywords:
            if kw in text_lower:
                if element not in found:
                    found.append(element)
                break
    return found[:3]


# ==================== 评分计算 ====================

def calculate_traffic_score(likes: int, comments: int, shares: int, author_followers: int) -> float:
    engagement = likes + comments * 2 + shares * 3
    if author_followers > 0:
        engagement_rate = engagement / author_followers
    else:
        engagement_rate = engagement / 10000
    
    base_score = min(likes / 100, 50)
    efficiency_bonus = min(engagement_rate * 100, 30)
    return min(100, base_score + efficiency_bonus)


def calculate_monetization_score(topic: str, ip_monetization: str, product_service: str) -> float:
    if not ip_monetization:
        return 50
    
    score = 50
    monetization_keywords = ip_monetization.lower()
    topic_keywords = topic.lower()
    
    high_value_words = ["赚钱", "变现", "创业", "副业", "收入", "投资", "理财", "加盟", "代理", "课程"]
    for word in high_value_words:
        if word in topic_keywords and word in monetization_keywords:
            score += 15
    
    if product_service:
        product_keywords = product_service.lower()
        common_words = set(topic_keywords.split()) & set(product_keywords.split())
        if common_words:
            score += len(common_words) * 5
    
    return min(100, score)


def calculate_fit_score(topic: str, ip_profile: Dict) -> float:
    if not ip_profile:
        return 50
    
    score = 50
    
    expertise = ip_profile.get("expertise", "")
    content_direction = ip_profile.get("content_direction", "")
    target_audience = ip_profile.get("target_audience", "")
    
    ip_keywords = f"{expertise} {content_direction} {target_audience}".lower()
    topic_lower = topic.lower()
    
    topic_words = set(re.findall(r'\w+', topic_lower))
    ip_words = set(re.findall(r'\w+', ip_keywords))
    
    common = topic_words & ip_words
    if common:
        overlap_ratio = len(common) / max(len(topic_words), 1)
        score += overlap_ratio * 40
    
    return min(100, score)


def calculate_cost_score(topic: str, viral_elements: List[str]) -> float:
    low_cost = ["分享", "观点", "经验", "故事", "建议", "方法", "技巧"]
    high_cost = ["测评", "对比", "开箱", "教程", "实操", "演示"]
    
    score = 70
    topic_lower = topic.lower()
    
    for indicator in low_cost:
        if indicator in topic_lower:
            score += 10
    
    for indicator in high_cost:
        if indicator in topic_lower:
            score -= 15
    
    if len(viral_elements) >= 2:
        score += 10
    
    return max(0, min(100, score))


def calculate_overall_score(topic_score: TopicScore, weights: Dict[str, int]) -> float:
    total = (
        topic_score.traffic_score * weights.get("traffic", 30) / 100 +
        topic_score.monetization_score * weights.get("monetization", 30) / 100 +
        topic_score.fit_score * weights.get("fit", 25) / 100 +
        topic_score.cost_score * weights.get("cost", 15) / 100
    )
    return round(total, 1)


# ==================== TIKHUB数据获取 ====================

def _check_tikhub_available() -> bool:
    """检查TIKHUB是否可用"""
    return os.environ.get("TIKHUB_API_KEY") and len(os.environ.get("TIKHUB_API_KEY", "")) > 0


async def _fetch_tikhub_topics(keywords: List[str], limit: int) -> List[Dict]:
    """从TIKHUB获取真实低粉爆款数据"""
    topics = []
    seen_titles = set()
    
    try:
        from app.services import tikhub_client
        
        # Debug: Check if configured
        is_cfg = tikhub_client.is_configured()
        print(f"TIKHUB is_configured: {is_cfg}")
        
        if not is_cfg:
            print("TIKHUB not configured, returning empty")
            return []
        
        print("Fetching from TIKHUB...")
        
        # 1. 获取抖音低粉爆款榜 (<10万粉, >1万赞)
        raw = await tikhub_client.fetch_douyin_low_fan_hot_list(
            page=1,
            page_size=min(limit * 2, 30),
            date_window=3,  # 近3天
        )
        items = tikhub_client.parse_low_fan_explosion_items(raw)
        
        for item in items:
            title = item.get("title", "")
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            
            # 关键词过滤
            if keywords and not any(kw.lower() in title.lower() for kw in keywords):
                continue
            
            topics.append({
                "title": title,
                "url": item.get("url", ""),
                "platform": "douyin",
                "likes": item.get("likes", 10000),
                "comments": item.get("comments", 500),
                "shares": item.get("shares", 100),
                "author_followers": item.get("author_followers", 5000),
                "source": "tikhub"
            })
            
            if len(topics) >= limit:
                break
        
        # 2. 如果不够，获取小红书话题
        if len(topics) < limit:
            topic_page_ids = os.environ.get("TIKHUB_XHS_TOPIC_PAGE_IDS", "").split(",")
            for page_id in topic_page_ids[:2]:
                if len(topics) >= limit:
                    break
                try:
                    feed = await tikhub_client.fetch_xhs_topic_feed(page_id.strip(), sort="hot")
                    notes = tikhub_client.parse_xhs_topic_feed_notes(feed)
                    
                    for note in notes[:5]:
                        title = note.get("title", "")
                        if not title or title in seen_titles:
                            continue
                        seen_titles.add(title)
                        
                        topics.append({
                            "title": title,
                            "url": note.get("url", ""),
                            "platform": "xiaohongshu",
                            "likes": note.get("likes", 8000),
                            "comments": note.get("comments", 300),
                            "shares": note.get("shares", 50),
                            "author_followers": note.get("author_followers", 3000),
                            "source": "tikhub"
                        })
                except:
                    pass
        
    except Exception as e:
        print(f"TIKHUB fetch error: {e}")
    
    return topics[:limit]


# ==================== 算法生成选题 ====================

def _generate_algorithm_topics(keywords: List[str], limit: int, ip_profile: Dict) -> List[Dict]:
    """用算法生成选题（TIKHUB失败时的兜底）"""
    kw = keywords[0] if keywords else "健康"
    
    # 基于IP专业领域生成相关话题
    expertise = ip_profile.get("expertise", "")
    content_dir = ip_profile.get("content_direction", "")
    
    # 构造相关话题模板
    templates = [
        f"{kw}行业趋势分析",
        f"如何{kw}效果更好",
        f"{kw}赛道的创业机会",
        f"90%的人都{kw}错了",
        f"原来{kw}这么简单",
        f"{kw}的常见误区",
        f"你必须知道的{kw}知识",
        f"{kw}如何帮你赚钱",
    ]
    
    # 如果有专业领域，添加更多相关话题
    if expertise:
        templates.extend([
            f"{expertise}从业者必看",
            f"{expertise}避坑指南",
        ])
    
    topics = []
    for i, title in enumerate(templates[:limit]):
        topics.append({
            "title": title,
            "url": "",
            "platform": "algorithm",
            "likes": 10000 - i * 1000,  # 模拟数据
            "comments": 500 - i * 50,
            "shares": 100 - i * 10,
            "author_followers": 5000,
            "source": "algorithm"
        })
    
    return topics


# ==================== 主推荐逻辑 ====================

async def recommend_topics(db: Session, ip_id: str, limit: int = 12) -> List[TopicScore]:
    """智能选题推荐 - TIKHUB优先 + 算法兜底"""
    
    # 1. 获取IP信息
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        return []
    
    ip_profile = {
        "expertise": ip.expertise or "",
        "content_direction": ip.content_direction or "",
        "target_audience": ip.target_audience or "",
        "monetization_model": ip.monetization_model or "",
        "product_service": ip.product_service or "",
    }
    
    # 策略配置
    strategy = get_merged_config(db, ip_id)
    weights = strategy.get("four_dim_weights", {
        "traffic": 30, "monetization": 30, "fit": 25, "cost": 15,
    })
    
    # 2. 提取IP关键词
    keywords = _extract_ip_keywords(ip)
    
    # 3. TIKHUB优先获取真实数据
    raw_topics = await _fetch_tikhub_topics(keywords, limit)
    
    # 4. 如果TIKHUB没数据，用算法生成
    if not raw_topics:
        raw_topics = _generate_algorithm_topics(keywords, limit, ip_profile)
    
    # 5. 评分
    scored_topics = []
    for topic_data in raw_topics:
        topic = topic_data.get("title", "")
        url = topic_data.get("url", "")
        
        likes = topic_data.get("likes", 0)
        comments = topic_data.get("comments", 0)
        shares = topic_data.get("shares", 0)
        author_followers = topic_data.get("author_followers", 0)
        source = topic_data.get("source", "algorithm")
        
        viral_elements = detect_viral_elements(topic)
        
        traffic = calculate_traffic_score(likes, comments, shares, author_followers)
        monetization = calculate_monetization_score(
            topic, ip_profile.get("monetization_model", ""), ip_profile.get("product_service", "")
        )
        fit = calculate_fit_score(topic, ip_profile)
        cost = calculate_cost_score(topic, viral_elements)
        
        topic_score = TopicScore(
            topic=topic, url=url, platform=topic_data.get("platform", "douyin"),
            traffic_score=traffic, monetization_score=monetization,
            fit_score=fit, cost_score=cost,
            likes=likes, comments=comments, shares=shares,
            author_followers=author_followers, viral_elements=viral_elements,
            source=source,
            overall_score=0, total_score=0,
        )
        
        topic_score.overall_score = calculate_overall_score(topic_score, weights)
        topic_score.total_score = traffic + monetization + fit + cost
        scored_topics.append(topic_score)
    
    # 6. 排序返回
    scored_topics.sort(key=lambda x: x.overall_score, reverse=True)
    return scored_topics[:limit]


def _extract_ip_keywords(ip: IP) -> List[str]:
    words = []
    for field in (ip.expertise, ip.content_direction, ip.target_audience, ip.passion, ip.market_demand):
        if field and isinstance(field, str):
            words.extend([w.strip() for w in re.split(r'[,，、\s]+', field) if len(w.strip()) >= 2])
    return list(set(words))[:20]


# ==================== API路由 ====================

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

router = APIRouter()


class TopicScoreResponse(BaseModel):
    topic: str
    url: str
    platform: str
    traffic_score: float
    monetization_score: float
    fit_score: float
    cost_score: float
    overall_score: float
    total_score: int
    viral_elements: List[str]
    source: str


@router.get("/strategy/topics/recommend", response_model=List[TopicScoreResponse])
async def recommend_topics_api(
    ip_id: str = Query(..., description="IP ID"),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """智能选题推荐接口 - TIKHUB优先 + 算法兜底"""
    results = await recommend_topics(db, ip_id, limit)
    
    return [
        TopicScoreResponse(
            topic=r.topic, url=r.url, platform=r.platform,
            traffic_score=r.traffic_score, monetization_score=r.monetization_score,
            fit_score=r.fit_score, cost_score=r.cost_score,
            overall_score=r.overall_score, total_score=r.total_score,
            viral_elements=r.viral_elements, source=r.source,
        )
        for r in results
    ]