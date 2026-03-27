"""
智能选题推荐服务
基于IP画像 + 低粉爆款数据 + 四维评分 = 数据驱动选题决策
"""
import os
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP
from app.services import tikhub_client
from app.services.ai_client import chat
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
    likes: int = 0             # 点赞数
    comments: int = 0          # 评论数
    shares: int = 0            # 分享数
    author_followers: int = 0 # 作者粉丝数
    viral_elements: List[str] = None  # 爆款元素
    
    def __post_init__(self):
        if self.viral_elements is None:
            self.viral_elements = []


# ==================== 爆款元素识别 ====================

VIRAL_ELEMENTS = {
    "cost": ["省钱", "免费", "便宜", "划算", "性价比", "亏", "花费", "预算"],
    "crowd": ["大家", "很多人", "都在", "你身边", "同龄人", "别人", "都", "教你"],
    "weird": ["奇怪", "没想到", "居然", "竟然", "颠覆", "反直觉", "意外", "揭秘"],
    "worst": ["最差", "踩坑", "后悔", "避坑", "教训", "毁掉", "糟糕", "别再"],
    "contrast": ["但是", "然而", "其实", "原来", "对比", "天壤之别", "差距", "不同"],
    "nostalgia": ["以前", "当年", "回忆", "曾经", "时光", "小时候", "青春"],
    "hormone": ["激动", "兴奋", "爽", "燃", "眼泪", "破防", "绷不住", "太好"],
    "top": ["第一", "最强", "顶级", "天花板", "巅峰", "冠军", "必看", "必收"],
}


def detect_viral_elements(text: str) -> List[str]:
    """检测文本中的爆款元素"""
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

def calculate_traffic_score(
    likes: int,
    comments: int,
    shares: int,
    author_followers: int,
) -> float:
    """
    流量潜力评分
    - 点赞/粉丝比 (互动效率)
    - 评论热度
    - 分享传播度
    """
    # 互动率 = (点赞+评论+分享) / 粉丝数
    engagement = likes + comments * 2 + shares * 3  # 分享权重更高
    if author_followers > 0:
        engagement_rate = engagement / author_followers
    else:
        engagement_rate = engagement / 10000  # 假设1万粉
    
    # 基础分 + 互动效率加分
    base_score = min(likes / 100, 50)  # 点赞带来的基础分
    efficiency_bonus = min(engagement_rate * 100, 30)  # 互动效率加分
    
    return min(100, base_score + efficiency_bonus)


def calculate_monetization_score(
    topic: str,
    ip_monetization: str,
    product_service: str,
) -> float:
    """
    变现关联评分
    - 话题与变现产品的关联度
    - 目标受众购买意向
    """
    if not ip_monetization:
        return 50  # 默认中等
    
    # 关键词匹配
    score = 50
    monetization_keywords = ip_monetization.lower()
    topic_keywords = topic.lower()
    
    # 高价值关键词加分
    high_value_words = ["赚钱", "变现", "创业", "副业", "收入", "投资", "理财", "加盟", "代理", "课程"]
    for word in high_value_words:
        if word in topic_keywords and word in monetization_keywords:
            score += 15
    
    # 产品相关度
    if product_service:
        product_keywords = product_service.lower()
        common_words = set(topic_keywords.split()) & set(product_keywords.split())
        if common_words:
            score += len(common_words) * 5
    
    return min(100, score)


def calculate_fit_score(
    topic: str,
    ip_profile: Dict,
) -> float:
    """
    IP契合度评分
    - 话题与IP专业领域
    - 目标受众匹配
    - 内容方向一致
    """
    if not ip_profile:
        return 50
    
    score = 50
    
    # 专业领域匹配
    expertise = ip_profile.get("expertise", "")
    content_direction = ip_profile.get("content_direction", "")
    target_audience = ip_profile.get("target_audience", "")
    
    ip_keywords = f"{expertise} {content_direction} {target_audience}".lower()
    topic_lower = topic.lower()
    
    # 计算关键词重叠
    topic_words = set(re.findall(r'\w+', topic_lower))
    ip_words = set(re.findall(r'\w+', ip_keywords))
    
    common = topic_words & ip_words
    if common:
        # 有交集，加分
        overlap_ratio = len(common) / max(len(topic_words), 1)
        score += overlap_ratio * 40
    
    return min(100, score)


def calculate_cost_score(
    topic: str,
    viral_elements: List[str],
) -> float:
    """
    制作成本评分
    - 简单话题（口播为主）= 低成本
    - 复杂话题（需要演示道具）= 高成本
    """
    # 低成本特征
    low_cost_indicators = ["分享", "观点", "经验", "故事", "建议", "方法", "技巧"]
    high_cost_indicators = ["测评", "对比", "开箱", "教程", "实操", "演示"]
    
    score = 70  # 基础分
    
    topic_lower = topic.lower()
    
    # 低成本加分
    for indicator in low_cost_indicators:
        if indicator in topic_lower:
            score += 10
    
    # 高成本减分
    for indicator in high_cost_indicators:
        if indicator in topic_lower:
            score -= 15
    
    # 爆款元素带来的自然流量 = 成本降低
    if len(viral_elements) >= 2:
        score += 10
    
    return max(0, min(100, score))


def calculate_overall_score(
    topic_score: TopicScore,
    weights: Dict[str, int],
) -> float:
    """计算加权综合评分"""
    total = (
        topic_score.traffic_score * weights.get("traffic", 30) / 100 +
        topic_score.monetization_score * weights.get("monetization", 30) / 100 +
        topic_score.fit_score * weights.get("fit", 25) / 100 +
        topic_score.cost_score * weights.get("cost", 15) / 100
    )
    return round(total, 1)


# ==================== 主推荐逻辑 ====================

async def recommend_topics(
    db: Session,
    ip_id: str,
    limit: int = 12,
) -> List[TopicScore]:
    """
    智能选题推荐
    
    流程：
    1. 获取IP画像和策略配置
    2. 抓取低粉爆款数据（抖音+小红书）
    3. 对每个话题进行四维评分
    4. 按综合评分排序返回
    """
    # 1. 获取IP信息
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        return []
    
    # IP画像
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
        "traffic": 30,
        "monetization": 30,
        "fit": 25,
        "cost": 15,
    })
    
    # 2. 提取IP关键词
    keywords = _extract_ip_keywords(ip)
    
    # 3. 抓取低粉爆款
    raw_topics = await _fetch_low_fan_topics(keywords, limit * 2)
    
    # 4. 评分
    scored_topics = []
    for topic_data in raw_topics:
        topic = topic_data.get("title", "")
        url = topic_data.get("url", "")
        
        # 提取互动数据（如果有）
        likes = topic_data.get("likes", 0)
        comments = topic_data.get("comments", 0)
        shares = topic_data.get("shares", 0)
        author_followers = topic_data.get("author_followers", 0)
        
        # 检测爆款元素
        viral_elements = detect_viral_elements(topic)
        
        # 四维评分
        traffic = calculate_traffic_score(likes, comments, shares, author_followers)
        monetization = calculate_monetization_score(
            topic,
            ip_profile.get("monetization_model", ""),
            ip_profile.get("product_service", "")
        )
        fit = calculate_fit_score(topic, ip_profile)
        cost = calculate_cost_score(topic, viral_elements)
        
        topic_score = TopicScore(
            topic=topic,
            url=url,
            platform=topic_data.get("platform", "douyin"),
            traffic_score=traffic,
            monetization_score=monetization,
            fit_score=fit,
            cost_score=cost,
            likes=likes,
            comments=comments,
            shares=shares,
            author_followers=author_followers,
            viral_elements=viral_elements,
            overall_score=0,
            total_score=0,
        )
        
        # 计算综合评分
        topic_score.overall_score = calculate_overall_score(topic_score, weights)
        topic_score.total_score = traffic + monetization + fit + cost
        
        scored_topics.append(topic_score)
    
    # 5. 排序并返回
    scored_topics.sort(key=lambda x: x.overall_score, reverse=True)
    return scored_topics[:limit]


def _extract_ip_keywords(ip: IP) -> List[str]:
    """从IP提取关键词"""
    words = []
    for field in (
        ip.expertise,
        ip.content_direction,
        ip.target_audience,
        ip.passion,
        ip.market_demand,
    ):
        if field and isinstance(field, str):
            # 简单分词
            words.extend([w.strip() for w in re.split(r'[,，、\s]+', field) if len(w.strip()) >= 2])
    return list(set(words))[:20]


async def _fetch_low_fan_topics(keywords: List[str], limit: int) -> List[Dict]:
    """抓取低粉爆款话题"""
    topics = []
    seen_urls = set()
    
    # 1. 抖音低粉爆款榜
    if tikhub_client.is_configured():
        try:
            raw = await tikhub_client.fetch_douyin_low_fan_hot_list(
                page=1,
                page_size=min(limit, 20),
                date_window=3,  # 近3天
            )
            items = tikhub_client.parse_low_fan_explosion_items(raw)
            
            for item in items:
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                title = item.get("title", "")
                # 过滤低相关度
                if keywords and not any(kw.lower() in title.lower() for kw in keywords):
                    continue
                
                topics.append({
                    "title": title,
                    "url": url,
                    "platform": "douyin",
                    "likes": item.get("likes", 0),
                    "comments": item.get("comments", 0),
                    "author_followers": item.get("author_followers", 0),
                })
        except Exception as e:
            print(f"抖音低粉爆款抓取失败: {e}")
    
    # 2. 小红书话题（如果有配置）
    topic_page_ids = os.environ.get("TIKHUB_XHS_TOPIC_PAGE_IDS", "").split(",")
    for page_id in topic_page_ids[:3]:
        if len(topics) >= limit:
            break
        try:
            feed = await tikhub_client.fetch_xhs_topic_feed(page_id.strip(), sort="hot")
            notes = tikhub_client.parse_xhs_topic_feed_notes(feed)
            
            for note in notes[:5]:
                url = note.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                topics.append({
                    "title": note.get("title", ""),
                    "url": url,
                    "platform": "xiaohongshu",
                    "likes": note.get("likes", 0),
                    "comments": note.get("comments", 0),
                    "author_followers": note.get("author_followers", 0),
                })
        except Exception as e:
            print(f"小红书话题抓取失败: {e}")
    
    return topics[:limit]


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


@router.get("/strategy/topics/recommend", response_model=List[TopicScoreResponse])
async def recommend_topics_api(
    ip_id: str = Query(..., description="IP ID"),
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """智能选题推荐接口"""
    results = await recommend_topics(db, ip_id, limit)
    
    return [
        TopicScoreResponse(
            topic=r.topic,
            url=r.url,
            platform=r.platform,
            traffic_score=r.traffic_score,
            monetization_score=r.monetization_score,
            fit_score=r.fit_score,
            cost_score=r.cost_score,
            overall_score=r.overall_score,
            total_score=r.total_score,
            viral_elements=r.viral_elements,
        )
        for r in results
    ]


@router.get("/strategy/topics/analyze")
async def analyze_topic(
    topic: str = Query(..., description="话题标题"),
    ip_id: str = Query(..., description="IP ID"),
    db: Session = Depends(get_db),
):
    """分析单个话题的评分详情"""
    ip = db.query(IP).filter(IP.ip_id == ip_id).first()
    if not ip:
        return {"error": "IP不存在"}
    
    ip_profile = {
        "expertise": ip.expertise or "",
        "content_direction": ip.content_direction or "",
        "target_audience": ip.target_audience or "",
        "monetization_model": ip.monetization_model or "",
        "product_service": ip.product_service or "",
    }
    
    viral_elements = detect_viral_elements(topic)
    
    return {
        "topic": topic,
        "viral_elements": viral_elements,
        "traffic_score": calculate_traffic_score(1000, 100, 50, 5000),
        "monetization_score": calculate_monetization_score(
            topic,
            ip_profile.get("monetization_model", ""),
            ip_profile.get("product_service", "")
        ),
        "fit_score": calculate_fit_score(topic, ip_profile),
        "cost_score": calculate_cost_score(topic, viral_elements),
    }
