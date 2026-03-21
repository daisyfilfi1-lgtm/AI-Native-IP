"""
热点追踪服务
实时接入各平台热点，结合IP生成选题
"""
import os
from typing import Any, Dict, List, Optional
import requests
from pydantic import BaseModel
from app.services.ai_client import chat, get_ai_config


class TrendingTopic(BaseModel):
    """热点话题"""
    platform: str      # 来源平台
    title: str         # 话题标题
    hot_score: float   # 热度指数
    category: str      # 分类
    url: Optional[str] = None


class HotTopicService:
    """
    热点追踪服务
    支持多平台热点接入
    """
    
    # 热点API配置
    BRAVE_SEARCH_API_KEY = os.environ.get("BRAVE_API_KEY")
    
    def __init__(self):
        self.cfg = get_ai_config()
    
    async def fetch_trending(self, platform: str = "all") -> List[TrendingTopic]:
        """
        获取热点话题
        
        Args:
            platform: 平台 (weibo/douyin/xiaohongshu/twitter/all)
        """
        if platform in ("weibo", "all"):
            topics = await self._fetch_weibo()
            if topics:
                return topics
        
        if platform in ("douyin", "all"):
            topics = await self._fetch_douyin()
            if topics:
                return topics
        
        if platform in ("twitter", "all"):
            topics = await self._fetch_twitter()
            if topics:
                return topics
        
        # 默认返回通用热点
        return await self._fetch_general()
    
    async def _fetch_weibo(self) -> List[TrendingTopic]:
        """微博热搜（模拟）"""
        # TODO: 接入真实API或爬虫
        return [
            TrendingTopic(
                platform="微博",
                title="AI医疗突破",
                hot_score=95.5,
                category="科技",
            ),
            TrendingTopic(
                platform="微博",
                title="两会健康政策",
                hot_score=88.3,
                category="政策",
            ),
            TrendingTopic(
                platform="微博",
                title="春季养生指南",
                hot_score=82.1,
                category="健康",
            ),
        ]
    
    async def _fetch_douyin(self) -> List[TrendingTopic]:
        """抖音热搜（模拟）"""
        return [
            TrendingTopic(
                platform="抖音",
                title="网红医生日常",
                hot_score=92.0,
                category="医疗",
            ),
            TrendingTopic(
                platform="抖音",
                title="健康科普短视频",
                hot_score=85.5,
                category="科普",
            ),
        ]
    
    async def _fetch_twitter(self) -> List[TrendingTopic]:
        """Twitter trending"""
        if not self.BRAVE_SEARCH_API_KEY:
            return []
        
        # 使用Brave Search API
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "X-Subscription-Token": self.BRAVE_SEARCH_API_KEY,
        }
        params = {
            "q": "healthcare AI",
            "count": 10,
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            data = resp.json()
            
            topics = []
            for item in data.get("web", {}).get("results", [])[:5]:
                topics.append(TrendingTopic(
                    platform="Twitter",
                    title=item.get("title", ""),
                    hot_score=80.0,
                    category="Tech",
                    url=item.get("url"),
                ))
            return topics
        except Exception:
            return []
    
    async def _fetch_general(self) -> List[TrendingTopic]:
        """通用热点（基于LLM生成）"""
        # 如果没有API，用LLM生成推荐话题
        return [
            TrendingTopic(
                platform="推荐",
                title="行业趋势分析",
                hot_score=75.0,
                category="通用",
            ),
            TrendingTopic(
                platform="推荐",
                title="用户常见问题解答",
                hot_score=70.0,
                category="问答",
            ),
            TrendingTopic(
                platform="推荐",
                title="专业知识分享",
                hot_score=68.0,
                category="教育",
            ),
        ]


class TopicRecommender:
    """
    话题推荐器
    结合IP画像和热点，推荐最佳选题
    """
    
    def __init__(self, ip_profile: Dict):
        self.ip_profile = ip_profile
        self.cfg = get_ai_config()
        self.hot_service = HotTopicService()
    
    async def recommend(
        self,
        platform: str = "all",
        count: int = 5,
    ) -> List[Dict]:
        """
        推荐选题
        
        Returns:
            [
                {
                    "topic": "话题",
                    "platform": "来源",
                    "score": 0.85,
                    "angle": "切入角度",
                    "form": "建议形式"
                },
                ...
            ]
        """
        # 1. 获取热点
        trending = await self.hot_service.fetch_trending(platform)
        
        if not trending:
            return []
        
        # 2. 构建分析提示
        topics_text = "\n".join([
            f"- {t.title} (热度:{t.hot_score}, 分类:{t.category})"
            for t in trending[:10]
        ])
        
        prompt = f"""你是内容策略专家。请分析以下热点话题，为IP推荐最佳选题。

## IP画像
- 领域专长: {self.ip_profile.get("expertise", "")}
- 内容风格: {self.ip_profile.get("content_direction", "")}
- 目标受众: {self.ip_profile.get("target_audience", "")}

## 热点话题
{topics_text}

请输出最推荐的5个选题，每个包含：
1. 话题
2. 相关性评分(0-1)
3. 切入角度
4. 建议内容形式

用JSON数组格式返回。"""
        
        try:
            # 3. LLM分析
            result = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[
                    {"role": "system", "content": "你是一个专业的内容策略专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
            )
            
            # 4. 解析结果
            import json
            # 尝试提取JSON
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]
            
            recommendations = json.loads(result.strip())
            return recommendations[:count]
            
        except Exception as e:
            print(f"Topic recommendation error: {e}")
            return []


# ==================== 便捷函数 ====================

async def get_trending_topics(platform: str = "all") -> List[TrendingTopic]:
    """获取热点话题"""
    service = HotTopicService()
    return await service.fetch_trending(platform)


async def recommend_topics(
    ip_profile: Dict,
    platform: str = "all",
    count: int = 5,
) -> List[Dict]:
    """为IP推荐选题"""
    recommender = TopicRecommender(ip_profile)
    return await recommender.recommend(platform, count)
