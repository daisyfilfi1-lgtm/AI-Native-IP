"""
内容生成管道 - 三大场景
场景一：热点选题 + IP匹配 + 一键生成
场景二：竞品爆款分析 + 改写生成
场景三：自定义原创 + IP风格 + 爆款逻辑
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.ai_client import chat, get_ai_config
from app.services.topic_service import HotTopicService, TopicRecommender


# ==================== 场景模型 ====================

class FourDimWeights(BaseModel):
    """四维权重"""
    relevance: float = Field(0.3, description="相关度权重")
    hotness: float = Field(0.3, description="热度权重")
    competition: float = Field(0.2, description="竞争度权重")
    conversion: float = Field(0.2, description="转化率权重")


class ScenarioOneRequest(BaseModel):
    """场景一：热点选题生成"""
    ip_id: str
    platform: str = Field("all", description="热点平台")
    ip_profile: Dict          # IP定位信息
    weights: FourDimWeights  # 四维权重
    count: int = Field(5, description="生成数量")


class ScenarioTwoRequest(BaseModel):
    """场景二：竞品爆款改写"""
    ip_id: str
    competitor_content: str = Field(..., description="竞品内容")
    competitor_platform: Optional[str] = Field(None, description="竞品平台")
    ip_profile: Dict         # IP定位信息
    rewrite_level: str = Field("medium", description="改写程度: light/medium/heavy")


class ScenarioThreeRequest(BaseModel):
    """场景三：自定义原创"""
    ip_id: str
    topic: str = Field(..., description="自定义话题")
    style_profile: Dict      # IP风格画像
    key_points: Optional[List[str]] = Field(None, description="关键要点")
    length: str = Field("medium", description="长度: short/medium/long")


class ContentResult(BaseModel):
    """内容生成结果"""
    content: str
    score: float = Field(0.0, description="质量评分")
    scenario: str            # 场景标识
    metadata: Dict = Field(default_factory=dict)


# ==================== 场景一：热点选题生成 ====================

class ScenarioOneGenerator:
    """
    场景一：热点选题 + 匹配度排序 + 一键生成
    流程：热点接入 → 相关度计算 → 排序选题 → 生成内容
    """
    
    def __init__(self, ip_profile: Dict, weights: FourDimWeights):
        self.ip_profile = ip_profile
        self.weights = weights
        self.cfg = get_ai_config()
        self.topic_service = HotTopicService()
    
    async def generate(self, platform: str = "all", count: int = 5) -> List[ContentResult]:
        """执行场景一"""
        
        # Step 1: 获取热点
        trending = await self.topic_service.fetch_trending(platform)
        
        # Step 2: 计算每个话题的四维得分
        scored_topics = []
        for topic in trending:
            scores = self._calculate_scores(topic)
            scored_topics.append({
                "topic": topic,
                "scores": scores,
                "total_score": sum([
                    scores["relevance"] * self.weights.relevance,
                    scores["hotness"] * self.weights.hotness,
                    scores["competition"] * self.weights.competition,
                    scores["conversion"] * self.weights.conversion,
                ])
            })
        
        # Step 3: 排序选题
        scored_topics.sort(key=lambda x: x["total_score"], reverse=True)
        selected = scored_topics[:count]
        
        # Step 4: 为每个选题生成内容
        results = []
        for item in selected:
            topic = item["topic"]
            content = await self._generate_content(topic.title, topic.category)
            
            results.append(ContentResult(
                content=content,
                score=item["total_score"],
                scenario="scenario_1",
                metadata={
                    "topic": topic.title,
                    "platform": topic.platform,
                    "hot_score": topic.hot_score,
                    "category": topic.category,
                    "relevance_score": item["scores"]["relevance"],
                }
            ))
        
        return results
    
    def _calculate_scores(self, topic) -> Dict[str, float]:
        """计算四维得分"""
        
        # 相关度：话题与IP领域的匹配程度
        relevance = self._calc_relevance(topic.title, topic.category)
        
        # 热度：话题本身的流量
        hotness = min(topic.hot_score / 100.0, 1.0)
        
        # 竞争度：越多人讨论，竞争越高（取反）
        competition = 1.0 - (hotness * 0.5)  # 简化计算
        
        # 转化率：话题对目标受众的转化潜力
        conversion = self._calc_conversion(topic.title, topic.category)
        
        return {
            "relevance": relevance,
            "hotness": hotness,
            "competition": competition,
            "conversion": conversion,
        }
    
    def _calc_relevance(self, title: str, category: str) -> float:
        """计算相关度"""
        # IP领域关键词
        ip_topics = self.ip_profile.get("expertise", "").split(",")
        ip_topics = [t.strip() for t in ip_topics if t.strip()]
        
        title_lower = title.lower()
        category_lower = category.lower()
        
        for topic in ip_topics:
            if topic.lower() in title_lower or topic.lower() in category_lower:
                return 0.9
        
        # LLM判断
        prompt = f"""判断话题与IP的相关程度（0-1）：

IP领域: {', '.join(ip_topics)}
话题: {title}
分类: {category}

直接输出数字。"""
        
        try:
            result = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            score = float(result.strip())
            return min(max(score, 0.0), 1.0)
        except:
            return 0.5
    
    def _calc_conversion(self, title: str, category: str) -> float:
        """计算转化率潜力"""
        # 高转化话题类型
        high_conv = ["测评", "教程", "推荐", "避坑", "省钱", "赚钱", "干货"]
        medium_conv = ["知识", "科普", "观点", "分析"]
        
        for kw in high_conv:
            if kw in title:
                return 0.9
        for kw in medium_conv:
            if kw in title:
                return 0.6
        
        return 0.5
    
    async def _generate_content(self, topic: str, category: str) -> str:
        """生成热点内容"""
        
        prompt = f"""你是一个资深的自媒体内容创作者。

## IP定位
- 领域: {self.ip_profile.get('expertise', '')}
- 风格: {self.ip_profile.get('content_direction', '')}
- 目标受众: {self.ip_profile.get('target_audience', '')}

## 热点话题
话题: {topic}
分类: {category}

## 要求
1. 结合热点话题，写出吸引眼球的标题
2. 内容有干货，有个人见解
3. 结构清晰，节奏明快
4. 适合短视频口播或图文发布
5. 长度适中（300-500字）

请生成内容："""
        
        result = chat(
            model=self.cfg.get("llm_model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        
        return result


# ==================== 场景二：竞品改写 ====================

class ScenarioTwoGenerator:
    """
    场景二：竞品爆款分析 + 改写生成
    流程：分析爆款结构 → 提取核心要素 → IP风格改写
    """
    
    def __init__(self, ip_profile: Dict):
        self.ip_profile = ip_profile
        self.cfg = get_ai_config()
    
    async def generate(
        self,
        competitor_content: str,
        platform: Optional[str] = None,
        rewrite_level: str = "medium",
    ) -> ContentResult:
        """执行场景二"""
        
        # Step 1: 分析竞品爆款结构
        structure = await self._analyze_structure(competitor_content, platform)
        
        # Step 2: 提取核心要素
        key_elements = self._extract_elements(competitor_content, structure)
        
        # Step 3: IP风格改写
        rewritten = await self._rewrite(key_elements, rewrite_level)
        
        # Step 4: 质量评分
        score = await self._score_quality(rewritten, structure)
        
        return ContentResult(
            content=rewritten,
            score=score,
            scenario="scenario_2",
            metadata={
                "original_structure": structure,
                "key_elements": key_elements,
                "rewrite_level": rewrite_level,
            }
        )
    
    async def _analyze_structure(self, content: str, platform: Optional[str]) -> Dict:
        """分析爆款结构"""
        
        prompt = f"""分析以下内容的爆款结构：

{content[:1500]}

平台: {platform or "未知"}

请分析：
1. 开头钩子（如何吸引眼球）
2. 内容框架（怎么展开）
3. 情绪曲线（如何调动情绪）
4. 结尾引导（如何引导互动）

输出JSON格式。"""
        
        try:
            result = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            
            import json
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            return json.loads(result.strip())
        except:
            return {"hook": "未知", "framework": "未知", "emotion": "未知", "ending": "未知"}
    
    def _extract_elements(self, content: str, structure: Dict) -> Dict:
        """提取核心要素"""
        
        prompt = f"""从以下内容中提取核心要素：

{content[:1000]}

爆款结构参考: {structure}

提取：
1. 核心观点/主题
2. 关键论据/案例
3. 金句/亮点
4. 引导互动的方式

输出JSON。"""
        
        try:
            result = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            
            import json
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            return json.loads(result.strip())
        except:
            return {"topic": "", "points": [], "highlights": [], "interaction": ""}
    
    async def _rewrite(self, elements: Dict, level: str) -> str:
        """IP风格改写"""
        
        # 改写程度映射
        level_map = {
            "light": "保持原文结构，只替换案例和表达方式",
            "medium": "保留核心观点，重新组织语言和案例",
            "heavy": "完全重构，提取内核后重新创作",
        }
        
        prompt = f"""你是一个自媒体内容创作者。

## IP定位
- 领域: {self.ip_profile.get('expertise', '')}
- 风格: {self.ip_profile.get('content_direction', '')}
- 受众: {self.ip_profile.get('target_audience', '')}

## 竞品爆款要素
{elements}

## 改写要求
{level_map.get(level, level_map['medium'])}

请用你的风格改写内容，保持爆款逻辑但具有个人特色。

要求：
1. 开头有钩子
2. 内容有干货
3. 结尾有引导
4. 300-500字

生成内容："""
        
        result = chat(
            model=self.cfg.get("llm_model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        
        return result
    
    async def _score_quality(self, content: str, structure: Dict) -> float:
        """质量评分"""
        
        prompt = f"""评估以下内容的质量（0-1）：

{content[:1000]}

参考爆款结构: {structure}

评估维度：
1. 原创度
2. 干货度
3. 情绪调动
4. 结构完整性

直接输出一个数字。"""
        
        try:
            result = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return float(result.strip())
        except:
            return 0.7


# ==================== 场景三：自定义原创 ====================

class ScenarioThreeGenerator:
    """
    场景三：自定义原创 + IP风格 + 爆款逻辑
    流程：用户输入 → 风格应用 → 爆款逻辑 → 生成内容
    """
    
    def __init__(self, ip_profile: Dict, style_profile: Dict):
        self.ip_profile = ip_profile
        self.style_profile = style_profile
        self.cfg = get_ai_config()
    
    async def generate(
        self,
        topic: str,
        key_points: Optional[List[str]] = None,
        length: str = "medium",
    ) -> ContentResult:
        """执行场景三"""
        
        # Step 1: 构建生成提示
        prompt = self._build_prompt(topic, key_points, length)
        
        # Step 2: 生成内容
        content = chat(
            model=self.cfg.get("llm_model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        
        # Step 3: 质量评分
        score = await self._score(content)
        
        return ContentResult(
            content=content,
            score=score,
            scenario="scenario_3",
            metadata={
                "topic": topic,
                "key_points": key_points or [],
                "length": length,
                "style_applied": True,
            }
        )
    
    def _build_prompt(
        self,
        topic: str,
        key_points: Optional[List[str]],
        length: str,
    ) -> str:
        """构建生成提示"""
        
        # 长度映射
        length_map = {
            "short": "150-250字",
            "medium": "300-500字",
            "long": "600-1000字",
        }
        
        # 风格特征
        style = self.style_profile or {}
        
        prompt = f"""你是一个资深的自媒体创作者。

## IP信息
- 名称: {self.ip_profile.get('name', 'IP')}
- 领域: {self.ip_profile.get('expertise', '')}
- 风格: {self.ip_profile.get('content_direction', '')}

## 你的风格特征
- 语气: {style.get('tone', '亲切专业')}
- 常用词: {', '.join(style.get('vocabulary', [])[:10])}
- 口头禅: {', '.join(style.get('catchphrases', [])[:3])}
- 句式: {', '.join(style.get('sentence_patterns', [])[:3])}

## 话题
{topic}

## 关键要点
{chr(10).join(f"- {p}" for p in (key_points or []))}

## 要求
1. 严格按照IP风格输出
2. 内容有个人见解和价值
3. 运用爆款逻辑：开头钩子 + 干货内容 + 情绪价值 + 结尾引导
4. 长度: {length_map.get(length, length_map['medium'])}

请生成内容："""
        
        return prompt
    
    async def _score(self, content: str) -> float:
        """质量评分"""
        
        prompt = f"""评估以下内容的质量（0-1）：

{content[:1000]}

评估维度：
1. 原创度
2. IP风格匹配度
3. 干货价值
4. 可读性

直接输出一个数字。"""
        
        try:
            result = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return float(result.strip())
        except:
            return 0.7


# ==================== 统一入口 ====================

class ContentGenerator:
    """内容生成统一入口"""
    
    @staticmethod
    async def scenario_one(request: ScenarioOneRequest) -> List[ContentResult]:
        """场景一：热点选题生成"""
        weights = request.weights or FourDimWeights()
        generator = ScenarioOneGenerator(request.ip_profile, weights)
        return await generator.generate(request.platform, request.count)
    
    @staticmethod
    async def scenario_two(request: ScenarioTwoRequest) -> ContentResult:
        """场景二：竞品改写生成"""
        generator = ScenarioTwoGenerator(request.ip_profile)
        return await generator.generate(
            request.competitor_content,
            request.competitor_platform,
            request.rewrite_level,
        )
    
    @staticmethod
    async def scenario_three(request: ScenarioThreeRequest) -> ContentResult:
        """场景三：自定义原创生成"""
        style = request.style_profile or {}
        generator = ScenarioThreeGenerator(request.ip_profile, style)
        return await generator.generate(request.topic, request.key_points, request.length)
