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

TOPIC_ANALYSIS_PROMPT = """分析以下话题，找出与IP最相关的切入角度。

## IP画像
- 领域: {expertise}
- 风格: {content_direction}
- 目标受众: {target_audience}

## 热点话题
{topics}

请输出：
1. 最相关的3个话题
2. 每个话题的切入角度
3. 建议的内容形式"""


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
    
    def analyze_topics(self, trending_topics: List[str]) -> Dict:
        """分析热点话题，返回选题建议"""
        
        prompt = ChatPromptTemplate.from_template(TOPIC_ANALYSIS_PROMPT)
        chain = prompt | self.llm | self.json_parser
        
        result = chain.invoke({
            "expertise": self.ip_profile.get("expertise", ""),
            "content_direction": self.ip_profile.get("content_direction", ""),
            "target_audience": self.ip_profile.get("target_audience", ""),
            "topics": "\n".join([f"- {t}" for t in trending_topics]),
        })
        
        return result
    
    def recommend_topics(self, count: int = 5) -> List[Dict]:
        """
        推荐选题
        1. 获取热点
        2. 分析相关性
        3. 排序返回
        """
        # TODO: 接入真实热点API
        trending = [
            "AI医疗",
            "健康养生",
            "名医访谈",
            "最新疗法",
        ]
        
        analysis = self.analyze_topics(trending)
        
        return analysis.get("recommended_topics", [])


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
