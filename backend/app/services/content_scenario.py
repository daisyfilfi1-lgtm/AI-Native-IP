"""
内容生成管道 - 三大场景
场景一：热点选题 + IP匹配 + 一键生成
场景二：竞品爆款分析 + 改写生成
场景三：自定义原创 + IP风格 + 爆款逻辑
"""
import os
from typing import Any, Dict, List, Optional
import re
from pydantic import BaseModel, Field

from app.services.ai_client import chat, get_ai_config
from app.services.style_corpus_service import StyleCorpusService
from app.services.topic_service import HotTopicService, TopicRecommender

REMIX_V2_ENABLED = os.getenv("REMIX_V2_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


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
        self.style_corpus = StyleCorpusService()
    
    async def generate(self, platform: str = "all", count: int = 5) -> List[ContentResult]:
        """执行场景一"""
        selected = await self.recommend_only(platform=platform, count=count)
        
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

    async def recommend_only(self, platform: str = "all", count: int = 5) -> List[Dict]:
        """仅推荐，不生成正文。"""
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
        return scored_topics[:count]
    
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
        style_layer = str(self.ip_profile.get("style_constraint_layer") or "").strip()
        style_examples = str(self.ip_profile.get("style_retrieved_examples_text") or "").strip()
        if not style_layer:
            retrieved = self.style_corpus.search_samples(
                topic=topic,
                emotion=str(self.ip_profile.get("content_direction") or ""),
                audience=str(self.ip_profile.get("target_audience") or ""),
                top_k=3,
            )
            style_layer = self.style_corpus.build_style_constraint_layer(retrieved)

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

{style_layer}

## 检索样本速览
{style_examples or "- （无）"}

请生成内容："""
        
        result = chat(
            model=self.cfg.get("llm_model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        
        style_diag = self.style_corpus.score_human_likeness(result or "")
        if not style_diag.get("pass"):
            repair_prompt = (
                prompt
                + "\n\n【对抗校验未通过，强制重写】\n"
                + f"- 问题：{'; '.join(style_diag.get('issues') or ['风格指标不足'])}\n"
                + "- 重写要求：提升句长波动、增加自然语气词与口语停顿、保持真实人味。\n"
                + "请仅输出修正版完整文案。"
            )
            repaired = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0.65,
            )
            if repaired and repaired.strip():
                result = repaired

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
        self.style_corpus = StyleCorpusService()

    def _normalize_input(self, competitor_content: str, platform: Optional[str]) -> Dict[str, Any]:
        raw = str(competitor_content or "")
        cleaned = re.sub(r"\n{3,}", "\n\n", raw).strip()
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        return {
            "platform": platform or "unknown",
            "raw_length": len(raw),
            "normalized_length": len(cleaned),
            "normalized_text": cleaned[:8000],
        }

    def _build_structure_snapshot(self, structure: Dict[str, Any], text: str) -> Dict[str, Any]:
        paras = [p.strip() for p in re.split(r"\n{2,}", text or "") if p.strip()]
        sents = [s.strip() for s in re.split(r"[。！？!?；;\n]+", text or "") if s.strip()]
        sentence_lengths = [len(s) for s in sents[:40]]
        return {
            "hook_type": str(structure.get("hook") or "unknown"),
            "emotion_curve": str(structure.get("emotion") or "unknown"),
            "framework": str(structure.get("framework") or "unknown"),
            "ending": str(structure.get("ending") or "unknown"),
            "paragraph_count": len(paras),
            "sentence_lengths": sentence_lengths,
        }

    def _build_retrieval_trace(self, elements: Dict[str, Any]) -> Dict[str, Any]:
        topic_hint = str(elements.get("topic") or self.ip_profile.get("content_direction") or "")
        audience = str(self.ip_profile.get("target_audience") or "")
        emotion = str(self.ip_profile.get("content_direction") or "")
        sample_ids = [str(x) for x in (self.ip_profile.get("style_retrieved_sample_ids") or []) if str(x).strip()]
        if not sample_ids:
            fallback = self.style_corpus.search_samples(topic=topic_hint, emotion=emotion, audience=audience, top_k=3)
            sample_ids = [str(x.get("sample_id") or "") for x in fallback if str(x.get("sample_id") or "").strip()]
        return {
            "query": self.style_corpus.build_retrieval_query(topic=topic_hint, emotion=emotion, audience=audience),
            "sample_ids": sample_ids[:3],
            "source": "pgvector" if self.ip_profile.get("style_retrieved_sample_ids") else "local_fallback",
        }

    def _build_validation_report(self, text: str, style_diag: Dict[str, Any]) -> Dict[str, Any]:
        domain_keywords = self._get_domain_whitelist()
        domain_hits = [k for k in domain_keywords if k in (text or "")]
        ip_id = str(self.ip_profile.get("ip_id") or "").strip().lower()
        self_name = str(self.ip_profile.get("self_name") or self.ip_profile.get("name") or "").strip()
        if ip_id == "xiaomin1":
            self_name = "小敏"
        banned_names = [str(x).strip() for x in (self.ip_profile.get("forbidden_self_names") or []) if str(x).strip()]
        ip_consistency = 1.0
        issues: List[str] = []
        # 结构优先：不再要求第一句自称，放宽为“前两句或前220字内出现身份标识”
        if self_name and self_name not in (text or "")[:220]:
            ip_consistency -= 0.1
            issues.append("身份标识出现偏后")
        if any(b and b in (text or "") for b in banned_names):
            ip_consistency -= 0.3
            issues.append("出现禁用称呼")
        if domain_keywords and not domain_hits:
            ip_consistency -= 0.3
            issues.append("未命中主题白名单")
        # 仿写 V2 门禁优先保障：主题聚焦 + IP一致性 + 无禁词
        # imperfection / burstiness 作为提示项，不阻断出稿
        no_banned_words = not bool(style_diag.get("banned_words_hit"))
        pass_all = no_banned_words and ip_consistency >= 0.8 and (not domain_keywords or bool(domain_hits))
        return {
            "ip_consistency_score": round(max(0.0, ip_consistency), 3),
            "domain_focus_hit": domain_hits,
            "burstiness_score": style_diag.get("burstiness_score"),
            "imperfection_score": style_diag.get("imperfection_score"),
            "issues": (style_diag.get("issues") or []) + issues,
            "pass": pass_all,
        }
    
    async def generate(
        self,
        competitor_content: str,
        platform: Optional[str] = None,
        rewrite_level: str = "medium",
    ) -> ContentResult:
        """执行场景二"""
        normalized = self._normalize_input(competitor_content, platform)

        # Step 1: 分析竞品爆款结构
        structure = await self._analyze_structure(normalized["normalized_text"], platform)
        structure_snapshot = self._build_structure_snapshot(structure, normalized["normalized_text"])
        
        # Step 2: 提取核心要素
        key_elements = self._extract_elements(normalized["normalized_text"], structure)
        retrieval_trace = self._build_retrieval_trace(key_elements)
        
        # Step 3: IP风格改写
        rewritten = await self._rewrite(key_elements, rewrite_level)
        # 预校正：先修复最常见提示项，减少无效重写
        rewritten = self._enforce_self_name_opening(rewritten)
        rewritten = self._boost_imperfection(rewritten)
        rewritten = self._force_domain_keyword(rewritten, self._get_domain_whitelist())
        
        # Step 4: 质量评分
        score = await self._score_quality(rewritten, structure)
        style_diag = self.style_corpus.score_human_likeness(rewritten or "")
        validation_report = self._build_validation_report(rewritten or "", style_diag)

        # V2: 对抗校验不通过 => 最多2轮强制重写
        if REMIX_V2_ENABLED and not validation_report.get("pass"):
            for _ in range(2):
                repair_prompt = (
                    "请对下面文案做纠偏重写，确保通过校验：\n"
                    f"- 问题: {'; '.join(validation_report.get('issues') or ['风格不稳定'])}\n"
                    f"- 必须命中主题词（若有）: {', '.join(self._get_domain_whitelist()) or '无'}\n"
                    "- 保持原有爆款结构，禁止泛泛鸡汤。\n\n"
                    f"原文：\n{rewritten}\n\n请输出修正版完整文案。"
                )
                retry = chat(
                    model=self.cfg.get("llm_model", "deepseek-chat"),
                    messages=[{"role": "user", "content": repair_prompt}],
                    temperature=0.45,
                )
                if retry and retry.strip():
                    rewritten = retry
                score = await self._score_quality(rewritten, structure)
                style_diag = self.style_corpus.score_human_likeness(rewritten or "")
                validation_report = self._build_validation_report(rewritten or "", style_diag)
                if validation_report.get("pass"):
                    break

            if not validation_report.get("pass"):
                rewritten = self._enforce_self_name_opening(rewritten)
                rewritten = self._boost_imperfection(rewritten)
                rewritten = self._force_domain_keyword(rewritten, self._get_domain_whitelist())
                score = await self._score_quality(rewritten, structure)
                style_diag = self.style_corpus.score_human_likeness(rewritten or "")
                validation_report = self._build_validation_report(rewritten or "", style_diag)
        
        return ContentResult(
            content=rewritten,
            score=score,
            scenario="scenario_2",
            metadata={
                "original_structure": structure,
                "structure_snapshot": structure_snapshot,
                "key_elements": key_elements,
                "rewrite_level": rewrite_level,
                "normalized_input": normalized,
                "retrieval_trace": retrieval_trace,
                "style_diagnostics": style_diag,
                "validation_report": validation_report,
                "remix_v2_enabled": REMIX_V2_ENABLED,
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

    def _get_domain_whitelist(self) -> List[str]:
        """
        小敏场景：强约束主题白名单，防止仿写跑偏到生活/健康等无关语境。
        """
        ip_id = str(self.ip_profile.get("ip_id") or "").strip().lower()
        ip_name = str(self.ip_profile.get("name") or "").strip().lower()
        self_name = str(self.ip_profile.get("self_name") or "").strip().lower()
        if ip_id == "xiaomin1" or ip_name in {"xiaomin1", "小敏"} or self_name in {"小敏", "xiaomin"}:
            return ["创业", "翻身", "变现", "私域"]
        return []

    def _domain_focus_ok(self, text: str, keywords: List[str]) -> bool:
        if not keywords:
            return True
        content = (text or "").strip()
        if not content:
            return False
        return any(k in content for k in keywords)

    def _force_domain_keyword(self, text: str, keywords: List[str]) -> str:
        """最终兜底：至少注入一个白名单词，避免主题跑偏无法识别。"""
        if not keywords:
            return text
        content = (text or "").strip()
        if not content or self._domain_focus_ok(content, keywords):
            return content
        forced = keywords[0]
        return f"{content}\n\n最后一句：别把希望交给运气，先从{forced}这件事开始，真金白银才会回来。"

    def _enforce_self_name_opening(self, text: str) -> str:
        content = (text or "").strip()
        if not content:
            return content
        ip_id = str(self.ip_profile.get("ip_id") or "").strip().lower()
        self_name = str(self.ip_profile.get("self_name") or self.ip_profile.get("name") or "").strip()
        if ip_id == "xiaomin1":
            self_name = "小敏"
        if not self_name:
            return content
        if self_name in content[:220]:
            return content
        # 不抢第一钩子：把身份信息插入到第一句后，保持结构自然
        first_break = content.find("。")
        if first_break == -1:
            return f"{content}（我是{self_name}）"
        head = content[: first_break + 1]
        tail = content[first_break + 1 :].lstrip()
        return f"{head}我是{self_name}，{tail}"

    def _boost_imperfection(self, text: str) -> str:
        content = (text or "").strip()
        if not content:
            return content
        if any(x in content for x in ["啊", "呢", "吧", "说实话"]):
            return content
        content = re.sub(r"。", "。说实话啊，", content, count=1)
        content = re.sub(r"但是", "但说实话啊", content, count=1)
        content = f"{content}\n\n你说是不是啊？我真是这么一路熬过来的。"
        return content
    
    async def _rewrite(self, elements: Dict, level: str) -> str:
        """IP风格改写"""
        
        # 改写程度映射
        level_map = {
            "light": "保持原文结构，只替换案例和表达方式",
            "medium": "保留核心观点，重新组织语言和案例",
            "heavy": "完全重构，提取内核后重新创作",
        }
        
        topic_hint = str(elements.get("topic") or self.ip_profile.get("content_direction") or "")
        style_layer = str(self.ip_profile.get("style_constraint_layer") or "").strip()
        style_examples = str(self.ip_profile.get("style_retrieved_examples_text") or "").strip()
        domain_keywords = self._get_domain_whitelist()
        domain_guard = (
            "## 主题硬约束\n"
            f"- 文案必须至少命中一个主题词：{', '.join(domain_keywords)}\n"
            "- 如果竞品素材偏生活/情绪表达，必须改写为创业经营、个人成长与商业变现语境。\n"
            "- 禁止输出纯生活感悟、情感鸡汤、健康科普导向内容。"
            if domain_keywords
            else ""
        )
        if not style_layer:
            retrieved = self.style_corpus.search_samples(
                topic=topic_hint,
                emotion=str(self.ip_profile.get("content_direction") or ""),
                audience=str(self.ip_profile.get("target_audience") or ""),
                top_k=3,
            )
            style_layer = self.style_corpus.build_style_constraint_layer(retrieved)

        prompt = f"""你是一个自媒体内容创作者。

## IP定位
- 领域: {self.ip_profile.get('expertise', '')}
- 风格: {self.ip_profile.get('content_direction', '')}
- 受众: {self.ip_profile.get('target_audience', '')}

## 竞品爆款要素
{elements}

## 改写要求
{level_map.get(level, level_map['medium'])}

{style_layer}
{domain_guard}

## 检索样本速览
{style_examples or "- （无）"}

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
        
        style_diag = self.style_corpus.score_human_likeness(result or "")
        if not style_diag.get("pass"):
            repair_prompt = (
                prompt
                + "\n\n【对抗校验未通过，强制重写】\n"
                + f"- 问题：{'; '.join(style_diag.get('issues') or ['风格指标不足'])}\n"
                + "- 重写要求：避免模板腔，增加口语不完美感和真实叙述感。\n"
                + "请输出修正版完整文案。"
            )
            repaired = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0.65,
            )
            if repaired and repaired.strip():
                result = repaired

        # 小敏主题强约束：跑偏时强制再重写一次
        if domain_keywords and not self._domain_focus_ok(result or "", domain_keywords):
            focus_repair = (
                prompt
                + "\n\n【主题纠偏重写】\n"
                + f"- 必须至少命中：{', '.join(domain_keywords)}\n"
                + "- 把竞品表达迁移到“创业实践/翻身路径/变现方法/私域经营”场景。\n"
                + "- 仍保持钩子-干货-引导结构，输出完整文案。"
            )
            focused = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": focus_repair}],
                temperature=0.6,
            )
            if focused and focused.strip():
                result = focused

        # 兜底：确保至少出现一个字面白名单词，便于前后链路一致识别
        if domain_keywords and not self._domain_focus_ok(result or "", domain_keywords):
            lexical_repair = (
                prompt
                + "\n\n【字面词硬约束】\n"
                + f"- 输出文本中必须至少出现以下原词之一：{', '.join(domain_keywords)}\n"
                + "- 可自然融入，不要生硬堆砌。\n"
                + "- 输出完整修正版。"
            )
            retry3 = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": lexical_repair}],
                temperature=0.5,
            )
            if retry3 and retry3.strip():
                result = retry3

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
        self.style_corpus = StyleCorpusService()
    
    async def generate(
        self,
        topic: str,
        key_points: Optional[List[str]] = None,
        length: str = "medium",
    ) -> ContentResult:
        """执行场景三"""
        
        # Step 1: 构建生成提示
        prompt = self._build_prompt(topic, key_points, length)
        
        # Step 2: 生成内容（含一次一致性失败自动重试）
        content = chat(
            model=self.cfg.get("llm_model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        consistency = self._consistency_check(content or "", topic, key_points)
        if consistency.get("overall", 0.0) < 0.78:
            repair_prompt = (
                prompt
                + "\n\n【纠偏指令】\n"
                + f"- 上一版问题: {', '.join(consistency.get('issues', [])) or '风格一致性不足'}\n"
                + "- 严格执行：自称、主题聚焦、禁用词、策略元素仅作表达策略。\n"
                + "- 现在请给出修正版完整文案。"
            )
            retry = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0.5,
            )
            if retry and retry.strip():
                content = retry
        style_diag = self.style_corpus.score_human_likeness(content or "")
        if not style_diag.get("pass"):
            repair_prompt = (
                prompt
                + "\n\n【对抗校验未通过，强制重写】\n"
                + f"- 问题：{'; '.join(style_diag.get('issues') or ['风格指标不足'])}\n"
                + "- 重写要求：去掉AI腔，增强口语化与自然瑕疵，保留真实人设和数据细节。\n"
                + "请直接输出修正版完整文案。"
            )
            retry2 = chat(
                model=self.cfg.get("llm_model", "deepseek-chat"),
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0.6,
            )
            if retry2 and retry2.strip():
                content = retry2
                style_diag = self.style_corpus.score_human_likeness(content or "")
        
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
                "style_diagnostics": style_diag,
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
        style_layer = str(self.ip_profile.get("style_constraint_layer") or "").strip()
        style_examples = str(self.ip_profile.get("style_retrieved_examples_text") or "").strip()
        if not style_layer:
            retrieved = self.style_corpus.search_samples(
                topic=topic,
                emotion=str(self.ip_profile.get("content_direction") or ""),
                audience=str(self.ip_profile.get("target_audience") or ""),
                top_k=3,
            )
            style_layer = self.style_corpus.build_style_constraint_layer(retrieved)
        
        self_name = (
            str(self.ip_profile.get("self_name") or "").strip()
            or str(self.ip_profile.get("nickname") or "").strip()
            or str(self.ip_profile.get("name") or "IP").strip()
        )
        banned_self_names = [n for n in {str(self.ip_profile.get("name") or "").strip()} if n and n != self_name]
        banned_self_names.extend(
            [
                str(x).strip()
                for x in (self.ip_profile.get("forbidden_self_names") or [])
                if str(x).strip()
            ]
        )
        # 去重保序
        _bn: List[str] = []
        for x in banned_self_names:
            if x not in _bn:
                _bn.append(x)
        banned_self_names = _bn
        viral_elements = [str(p) for p in (key_points or []) if str(p).strip()]
        strategy_template_name = str(self.ip_profile.get("strategy_template_name") or "").strip()
        strategy_template_instruction = str(self.ip_profile.get("strategy_template_instruction") or "").strip()
        style_evidence = self.ip_profile.get("style_evidence") or []
        style_evidence_text = "\n".join(
            f"- 证据{i+1}: {str(x)[:180]}" for i, x in enumerate(style_evidence[:4]) if str(x).strip()
        )
        self_intro = str(self.ip_profile.get("self_intro") or "").strip()
        few_shot_examples = self.ip_profile.get("few_shot_examples") or []
        few_shot_text = "\n".join(
            f"- 样本{i+1}: {str(x)[:260]}" for i, x in enumerate(few_shot_examples[:3]) if str(x).strip()
        )

        prompt = f"""你是一个资深的自媒体创作者。

## IP信息
- IP名称: {self.ip_profile.get('name', 'IP')}
- 文案自称: {self_name}
- 领域: {self.ip_profile.get('expertise', '')}
- 风格: {self.ip_profile.get('content_direction', '')}

## 你的风格特征
- 语气: {style.get('tone', '亲切专业')}
- 常用词: {', '.join(style.get('vocabulary', [])[:10])}
- 口头禅: {', '.join(style.get('catchphrases', [])[:3])}
- 句式: {', '.join(style.get('sentence_patterns', [])[:3])}

## 话题
{topic}

## 策略指令模板
- 选择模板: {strategy_template_name or "说观点"}
- 模板指令: {strategy_template_instruction or "开头钩子 + 干货论证 + 情绪价值 + CTA"}

## 爆款元素（表达策略，不是内容主题关键词）
{chr(10).join(f"- {p}" for p in viral_elements) if viral_elements else "- （无）"}

## 风格证据（来自知识库，必须尽量贴合）
{style_evidence_text or "- （无）"}

## 动态Few-shot样本（优先模仿结构与语感，不抄袭事实）
{few_shot_text or "- （无）"}

{style_layer}

## 检索样本速览
{style_examples or "- （无）"}

## 要求
1. 严格按照IP风格输出
2. 文案里自称必须使用「{self_name}」，禁止自称为其他名字（如：{', '.join(banned_self_names) if banned_self_names else '无'}）
2.1 开场优先使用该自我介绍语感（可同义改写，不要照抄）：{self_intro or "我是{self_name}"}
3. 内容必须围绕「话题」展开，爆款元素仅用于选角度/组织表达，禁止把爆款元素写成“文章围绕的三个关键词/三大主题”
4. 运用爆款逻辑：开头钩子 + 干货内容 + 情绪价值 + 结尾引导
5. 长度: {length_map.get(length, length_map['medium'])}

请生成内容："""
        
        return prompt

    def _consistency_check(self, content: str, topic: str, key_points: Optional[List[str]]) -> Dict[str, Any]:
        text = (content or "").strip()
        if not text:
            return {"overall": 0.0, "issues": ["空内容"]}
        issues: List[str] = []
        score = 1.0

        self_name = (
            str(self.ip_profile.get("self_name") or "").strip()
            or str(self.ip_profile.get("name") or "").strip()
        )
        if self_name and self_name not in text[:120]:
            score -= 0.2
            issues.append("开场未使用指定自称")

        banned = [str(x).strip() for x in (self.ip_profile.get("forbidden_self_names") or []) if str(x).strip()]
        for b in banned:
            if b and b in text:
                score -= 0.2
                issues.append(f"出现禁用称呼:{b}")
                break

        # 爆款元素不应被写成“主线三关键词”
        if re.search(r"(三个关键词|三大关键词|围绕.*关键词)", text):
            score -= 0.2
            issues.append("把策略元素写成了内容主线")
        for p in (key_points or []):
            if str(p) and f"围绕{p}" in text:
                score -= 0.1
                issues.append("策略元素被当作主题")
                break

        # 主题聚焦：至少命中一个主题词
        topic_tokens = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z0-9_]{2,}", topic or "")
        if topic_tokens:
            hit = any(t in text for t in topic_tokens[:6])
            if not hit:
                score -= 0.2
                issues.append("主题词命中不足")

        # 禁用大厂黑话（来自 IP克隆参考）
        blacklist = ["闭环", "赋能", "赛道", "颗粒度", "底层逻辑", "垂直领域"]
        if any(w in text for w in blacklist):
            score -= 0.1
            issues.append("出现禁用黑话")

        return {"overall": max(0.0, score), "issues": issues}
    
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
    async def scenario_one_recommend_topics(request: ScenarioOneRequest) -> List[Dict]:
        """场景一：仅推荐选题，不生成正文。"""
        weights = request.weights or FourDimWeights()
        generator = ScenarioOneGenerator(request.ip_profile, weights)
        return await generator.recommend_only(request.platform, request.count)
    
    @staticmethod
    async def scenario_one_generate_from_selected_topic(
        *,
        ip_profile: Dict,
        topic: str,
        category: str = "selected_topic",
    ) -> ContentResult:
        """场景一：基于已选题目生成正文（推荐与生成解耦后的第二步）"""
        generator = ScenarioOneGenerator(ip_profile or {}, FourDimWeights())
        content = await generator._generate_content(topic, category)
        score = generator._calc_relevance(topic, category)
        style_diag = generator.style_corpus.score_human_likeness(content or "")
        return ContentResult(
            content=content,
            score=score,
            scenario="scenario_1_selected_topic",
            metadata={"topic": topic, "category": category, "style_diagnostics": style_diag},
        )
    
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
        profile = request.style_profile or {}
        generator = ScenarioThreeGenerator(profile, profile)
        return await generator.generate(request.topic, request.key_points, request.length)
