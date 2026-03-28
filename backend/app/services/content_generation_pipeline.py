"""
内容生成管道 - LangChain LCEL实现
完整的IP内容生成流程：检索 → 重组 → 风格化 → 评分 → 合规
"""
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from langchain_core.runnables import (
    RunnableParallel,
    RunnablePassthrough,
    RunnableLambda,
)
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI

from app.services.ai_client import chat, get_ai_config


# ==================== Prompt模板 ====================

IP_STYLE_PROMPT = """你是一个资深的{ip_name}。

请根据以下素材和风格特征，生成符合IP风格的内容。

## IP风格特征
{style_features}

## 常用词汇
{vocabulary}

## 语气特征
{tone}

## 口头禅
{catchphrases}

## 参考素材
{reference_content}

## 话题/选题
{topic}

## 要求
1. 严格保持IP的说话风格
2. 内容原创，有个人见解
3. 结合热点，有价值
4. 长度适中，适合短视频口播

请生成内容："""

TOPIC_ANALYSIS_PROMPT = """你是短视频选题策划。根据 IP 画像与给定话题列表，输出严格 JSON（不要 markdown 代码块）。

## IP 画像
- 名称: {name}
- 领域: {expertise}
- 内容方向: {content_direction}
- 目标受众: {target_audience}
- 独特价值: {unique_value_prop}

## 候选话题（每行一条）
{topics}

## 爆款元素 id（每条选题从中选 2-3 个）
cost, crowd, weird, worst, contrast, nostalgia, hormone, top

## 输出 JSON 格式
{{
  "recommended_topics": [
    {{
      "title": "string",
      "score": 85,
      "reason": "string",
      "trend": "up",
      "viral_elements": ["cost", "crowd"]
    }}
  ],
  "analysis": "整体判断与建议（中文）"
}}

最多输出 8 条 recommended_topics，按 score 降序。"""


STRATEGY_RECOMMEND_JSON_PROMPT = """你是短视频选题策划。根据 IP 画像，直接产出适合该 IP 的短视频选题（中文）。

## IP 画像
- 名称: {name}
- 领域: {expertise}
- 内容方向: {content_direction}
- 目标受众: {target_audience}
- 独特价值: {unique_value_prop}

## 爆款元素 id（每条选题从中选 2-3 个）
cost, crowd, weird, worst, contrast, nostalgia, hormone, top

## 任务
请生成恰好 {count} 条「具体可拍」的选题标题，并评估爆款潜力分数 0-100。

只输出严格 JSON（不要 markdown 代码块），格式：
{{
  "recommended_topics": [
    {{
      "title": "string",
      "score": 88,
      "reason": "string",
      "trend": "up",
      "viral_elements": ["worst", "top"]
    }}
  ],
  "analysis": "选题策略简述（中文）"
}}"""


QUALITY_SCORING_PROMPT = """请评估以下内容的质量：

## 待评估内容
{content}

## IP风格特征
{style_features}

请从以下维度评分（0-1）：
1. 原创度 (originality)
2. 风格匹配度 (style_match)
3. 情感曲线 (emotion_curve)
4. 可读性 (readability)
5. 信息价值 (value)

请输出JSON格式：
{{
  "originality": 0.0-1.0,
  "style_match": 0.0-1.0,
  "emotion_curve": 0.0-1.0,
  "readability": 0.0-1.0,
  "value": 0.0-1.0,
  "overall": 0.0-1.0,
  "issues": ["问题列表"],
  "suggestions": ["改进建议"]
}}"""


# ==================== 内容生成管道 ====================

class ContentGenerationPipeline:
    """
    基于LangChain LCEL的内容生成管道
    """
    
    def __init__(self, ip_id: str, ip_profile: Dict):
        self.ip_id = ip_id
        self.ip_profile = ip_profile
        self.cfg = get_ai_config()
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=self.cfg.get("llm_model", "deepseek-chat"),
            openai_api_key=self.cfg.get("api_key"),
            base_url=self.cfg.get("base_url"),
            temperature=0.7,
        )
        
        self.output_parser = StrOutputParser()
        self.json_parser = JsonOutputParser()
    
    def _load_ip_style(self) -> Dict:
        """加载IP风格特征"""
        # TODO: 从数据库/记忆系统加载
        return {
            "ip_name": self.ip_profile.get("name", "IP"),
            "style_features": self.ip_profile.get("style_features", "专业、热情"),
            "vocabulary": self.ip_profile.get("vocabulary", "医疗、健康"),
            "tone": self.ip_profile.get("tone", "亲切专业"),
            "catchphrases": self.ip_profile.get("catchphrases", ""),
        }
    
    def _retrieve_assets(self, topic: str, top_k: int = 5) -> str:
        """检索相关素材"""
        # TODO: 接入已有的混合检索
        # 使用 Qdrant/Neo4j 检索
        return "检索到的相关素材内容..."
    
    def generate_content(
        self,
        topic: str,
        reference_assets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        生成完整内容流程
        
        1. 检索素材
        2. 构建提示词
        3. 生成初稿
        4. 质量评分
        5. 改进（如需要）
        """
        
        # Step 1: 加载IP风格
        style = self._load_ip_style()
        
        # Step 2: 检索素材
        assets_content = self._retrieve_assets(topic)
        
        # Step 3: 构建生成提示词
        prompt = ChatPromptTemplate.from_template(IP_STYLE_PROMPT)
        
        chain = prompt | self.llm | self.output_parser
        
        # 生成初稿
        draft = chain.invoke({
            "ip_name": style["ip_name"],
            "style_features": style["style_features"],
            "vocabulary": style["vocabulary"],
            "tone": style["tone"],
            "catchphrases": style["catchphrases"],
            "reference_content": assets_content,
            "topic": topic,
        })
        
        # Step 4: 质量评分
        quality = self._score_quality(draft, style)
        
        return {
            "draft": draft,
            "quality": quality,
            "style": style,
            "topic": topic,
        }
    
    def _score_quality(self, content: str, style: Dict) -> Dict:
        """质量评分"""
        prompt = ChatPromptTemplate.from_template(QUALITY_SCORING_PROMPT)
        
        chain = prompt | self.llm | self.json_parser
        
        try:
            scores = chain.invoke({
                "content": content[:2000],  # 限制长度
                "style_features": style.get("style_features", ""),
            })
            return scores
        except Exception as e:
            return {
                "overall": 0.8,
                "error": str(e)
            }
    
    def batch_generate(
        self,
        topics: List[str],
    ) -> List[Dict[str, Any]]:
        """批量生成内容"""
        results = []
        for topic in topics:
            result = self.generate_content(topic)
            results.append(result)
        return results


# ==================== 热点分析Agent ====================

class TopicStrategyAgent:
    """
    基于LangChain Agent的热点分析+选题Agent
    """
    
    def __init__(self, ip_id: str, ip_profile: Dict):
        self.ip_id = ip_id
        self.ip_profile = ip_profile
        self.cfg = get_ai_config()
        
        self.llm = ChatOpenAI(
            model=self.cfg.get("llm_model", "deepseek-chat"),
            openai_api_key=self.cfg.get("api_key"),
            base_url=self.cfg.get("base_url"),
            temperature=0.5,
        )
        self.json_parser = JsonOutputParser()
    
    def _normalize_topic_item(self, raw: Dict) -> Dict[str, Any]:
        allowed = {
            "cost",
            "crowd",
            "weird",
            "worst",
            "contrast",
            "nostalgia",
            "hormone",
            "top",
        }
        els = raw.get("viral_elements") or raw.get("elements") or []
        if not isinstance(els, list):
            els = []
        viral = [str(e).strip() for e in els if str(e).strip() in allowed]
        if len(viral) < 2:
            viral = (viral + ["crowd", "contrast"])[:3]
        score = raw.get("score", 0)
        try:
            score = int(float(score))
        except (TypeError, ValueError):
            score = 70
        score = max(0, min(100, score))
        trend = str(raw.get("trend", "stable")).lower()
        if trend not in ("up", "down", "stable"):
            trend = "stable"
        return {
            "title": str(raw.get("title", "")).strip() or "未命名选题",
            "score": score,
            "reason": str(raw.get("reason", "")).strip() or "—",
            "trend": trend,
            "viral_elements": viral[:3],
        }

    def analyze_topics(self, trending_topics: List[str]) -> Dict[str, Any]:
        """分析热点话题，返回选题建议（JSON）"""

        prompt = ChatPromptTemplate.from_template(TOPIC_ANALYSIS_PROMPT)
        chain = prompt | self.llm | self.json_parser

        try:
            result = chain.invoke(
                {
                    "name": self.ip_profile.get("name", ""),
                    "expertise": self.ip_profile.get("expertise", ""),
                    "content_direction": self.ip_profile.get("content_direction", ""),
                    "target_audience": self.ip_profile.get("target_audience", ""),
                    "unique_value_prop": self.ip_profile.get("unique_value_prop", ""),
                    "topics": "\n".join([f"- {t}" for t in trending_topics]),
                }
            )
        except Exception:
            return {
                "recommended_topics": [],
                "analysis": "话题分析失败，请稍后重试或检查模型配置。",
            }

        if not isinstance(result, dict):
            return {"recommended_topics": [], "analysis": str(result)}
        raw_list = result.get("recommended_topics") or []
        if not isinstance(raw_list, list):
            raw_list = []
        normalized = [self._normalize_topic_item(x) for x in raw_list if isinstance(x, dict)]
        normalized.sort(key=lambda x: x["score"], reverse=True)
        return {
            "recommended_topics": normalized,
            "analysis": str(result.get("analysis", "")).strip() or "—",
        }

    def recommend_topics(self, count: int = 5) -> Dict[str, Any]:
        """
        基于 IP 画像推荐选题。
        
        优先使用V4竞品爆款系统，如果失败则回退到LLM生成。
        """
        n = max(1, min(20, int(count)))
        
        # 尝试使用V4竞品爆款系统
        try:
            import asyncio
            from app.services.topic_recommendation_v4 import get_recommendation_service_v4
            
            # 获取数据库会话（从当前上下文中）
            # 注意：这里使用同步方式调用异步代码
            service = get_recommendation_service_v4()
            
            # 由于recommend_topics是异步的，我们需要创建一个新的事件循环
            # 或者使用已存在的事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果在已有事件循环中，使用run_coroutine_threadsafe
                    import concurrent.futures
                    executor = concurrent.futures.ThreadPoolExecutor()
                    future = executor.submit(
                        asyncio.run,
                        self._fetch_v4_topics(service, n)
                    )
                    v4_result = future.result(timeout=30)
                else:
                    v4_result = loop.run_until_complete(
                        self._fetch_v4_topics(service, n)
                    )
            except RuntimeError:
                # 没有事件循环，创建新的
                v4_result = asyncio.run(self._fetch_v4_topics(service, n))
            
            if v4_result and len(v4_result) > 0:
                # 转换V4结果为前端兼容格式
                normalized = self._convert_v4_to_legacy(v4_result)
                return {
                    "recommended_topics": normalized[:n],
                    "analysis": f"基于{len(v4_result)}个竞品爆款生成的推荐（V4系统）",
                }
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"[V4] Failed to use competitor topics: {e}")
        
        # 回退到LLM生成
        return self._recommend_topics_llm(n)
    
    async def _fetch_v4_topics(self, service, count: int):
        """异步获取V4选题"""
        # 这里需要数据库会话，我们通过依赖注入方式获取
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            return await service.recommend_topics(
                db=db,
                ip_id=self.ip_id,
                limit=count,
                strategy="competitor_first"
            )
        finally:
            db.close()
    
    def _convert_v4_to_legacy(self, v4_topics: List[Any]) -> List[Dict[str, Any]]:
        """将V4选题转换为前端兼容格式"""
        result = []
        for topic in v4_topics:
            # 提取爆款元素标签
            viral_elements = ["crowd", "contrast"]  # 默认元素
            if topic.content_type == "money":
                viral_elements = ["cost", "crowd"]
            elif topic.content_type == "emotion":
                viral_elements = ["nostalgia", "hormone"]
            elif topic.content_type == "skill":
                viral_elements = ["top", "contrast"]
            
            # 构建reason字段
            reason_parts = []
            if topic.is_remixed:
                reason_parts.append(f"[竞品重构] {topic.remix_reason}")
            if topic.competitor_author:
                reason_parts.append(f"参考: {topic.competitor_author}")
            if topic.competitor_play_count > 0:
                reason_parts.append(f"播放量: {topic.competitor_play_count/10000:.1f}万")
            
            reason = " | ".join(reason_parts) if reason_parts else topic.remix_reason or "—"
            
            item = {
                "title": topic.title,
                "score": int(topic.total_score * 20),  # 0-5分转换为0-100分
                "reason": reason,
                "trend": "up" if topic.competitor_play_count > 50000 else "stable",
                "viral_elements": viral_elements[:3],
                # V4 竞品系统字段（前端 TopicCard 直接展示）
                "competitor_name": topic.competitor_name,
                "competitor_platform": topic.competitor_platform,
                "remix_potential": topic.remix_potential,
                "viral_score": topic.viral_score,
                "original_plays": topic.original_plays,
                # 保留V4特有的字段供前端使用
                "_v4_data": {
                    "original_title": topic.original_title,
                    "is_remixed": topic.is_remixed,
                    "remix_confidence": topic.remix_confidence,
                    "competitor_author": topic.competitor_author,
                    "competitor_play_count": topic.competitor_play_count,
                    "content_type": topic.content_type,
                    "content_angle": topic.content_angle,
                    "competitor_name": topic.competitor_name,
                    "competitor_platform": topic.competitor_platform,
                    "remix_potential": topic.remix_potential,
                    "viral_score": topic.viral_score,
                    "original_plays": topic.original_plays,
                }
            }
            result.append(item)
        return result
    
    def _recommend_topics_llm(self, n: int) -> Dict[str, Any]:
        """
        使用LLM生成选题（回退方案）
        """
        prompt = ChatPromptTemplate.from_template(STRATEGY_RECOMMEND_JSON_PROMPT)
        chain = prompt | self.llm | self.json_parser
        try:
            result = chain.invoke(
                {
                    "name": self.ip_profile.get("name", ""),
                    "expertise": self.ip_profile.get("expertise", ""),
                    "content_direction": self.ip_profile.get("content_direction", ""),
                    "target_audience": self.ip_profile.get("target_audience", ""),
                    "unique_value_prop": self.ip_profile.get("unique_value_prop", ""),
                    "count": n,
                }
            )
        except Exception:
            return {
                "recommended_topics": [],
                "analysis": "推荐选题失败，请稍后重试或检查模型配置。",
            }

        if not isinstance(result, dict):
            return {"recommended_topics": [], "analysis": str(result)}
        raw_list = result.get("recommended_topics") or []
        if not isinstance(raw_list, list):
            raw_list = []
        normalized = [self._normalize_topic_item(x) for x in raw_list if isinstance(x, dict)]
        normalized.sort(key=lambda x: x["score"], reverse=True)
        return {
            "recommended_topics": normalized[:n],
            "analysis": str(result.get("analysis", "")).strip() or "—",
        }


# ==================== 质量评分服务 ====================

class QualityScorer:
    """
    独立的质量评分服务
    """
    
    def __init__(self):
        self.cfg = get_ai_config()
        self.llm = ChatOpenAI(
            model=self.cfg.get("llm_model", "deepseek-chat"),
            openai_api_key=self.cfg.get("api_key"),
            base_url=self.cfg.get("base_url"),
            temperature=0.3,
        )
        self.json_parser = JsonOutputParser()

    def score(self, content: str, ip_style: Optional[Dict] = None) -> Dict:
        """
        多维度质量评分
        """
        prompt = ChatPromptTemplate.from_template(QUALITY_SCORING_PROMPT)
        chain = prompt | self.llm | self.json_parser
        
        style_str = ""
        if ip_style:
            style_str = str(ip_style.get("style_features", ""))
        
        try:
            result = chain.invoke({
                "content": content[:2000],
                "style_features": style_str,
            })
            return result
        except Exception as e:
            return {
                "overall": 0.8,
                "error": str(e)
            }
    
    def batch_score(self, contents: List[str]) -> List[Dict]:
        """批量评分"""
        return [self.score(c) for c in contents]


# ==================== 便捷函数 ====================

def create_content_pipeline(ip_id: str, ip_profile: Dict) -> ContentGenerationPipeline:
    """创建内容生成管道"""
    return ContentGenerationPipeline(ip_id, ip_profile)


def create_strategy_agent(ip_id: str, ip_profile: Dict) -> TopicStrategyAgent:
    """创建策略Agent"""
    return TopicStrategyAgent(ip_id, ip_profile)
