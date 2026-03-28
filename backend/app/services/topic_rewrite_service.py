"""
热点话题智能改写服务

解决原系统的机械拼接问题，实现基于语义理解和IP定位的智能改写
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.services.keyword_synonyms import (
    classify_content_type, 
    get_content_type_name,
    CONTENT_TYPE_KEYWORDS,
    expand_keywords
)

logger = logging.getLogger(__name__)


class RewriteStrategy(Enum):
    """改写策略"""
    LLM_SEMANTIC = "llm_semantic"      # LLM语义改写（推荐）
    TEMPLATE_SMART = "template_smart"   # 智能模板改写
    KEYWORD_REPLACE = "keyword_replace" # 关键词替换（保底）


@dataclass
class RewriteResult:
    """改写结果"""
    original_title: str
    rewritten_title: str
    content_type: str              # money/emotion/skill/life
    strategy: RewriteStrategy      # 使用的改写策略
    quality_score: float           # 改写质量分 (0-1)
    ip_keywords_matched: List[str] # 匹配的IP关键词
    reason: str                    # 改写说明


class TopicRewriteService:
    """
    热点话题智能改写服务
    
    核心改进：
    1. 基于内容类型选择改写策略
    2. 使用语义理解而非机械拼接
    3. 保留原标题的核心信息
    4. 添加改写质量评估
    """
    
    def __init__(self):
        # 原系统的机械改写模板（用于对比）
        self._old_templates = [
            "{title}：从创业到翻身的可复制打法",
            "{title}：{kw1}如何帮她实现{kw2}",
        ]
        
        # 新系统的智能改写模板（按内容类型）
        self._smart_templates = {
            "money": {  # 搞钱方法论
                "high_engagement": [
                    "{title}，她用这个方法月入{income}",
                    "从0到月入{income}：{title}的完整复盘",
                    "{title}，普通人复制的3个关键点",
                    "她用{title}实现月入{income}，你也可以",
                ],
                "tutorial": [
                    "{title}，手把手教你月入{income}",
                    "{title}的完整攻略，建议收藏",
                    "月入{income}的秘密：{title}",
                ],
            },
            "emotion": {  # 情感共情
                "story": [
                    "{title}，她花了{time}才走出来",
                    "从{title}到逆袭，她做对了什么",
                    "{title}，但最终她选择了{choice}",
                    "她说：{title}不是终点，而是起点",
                ],
                "empathy": [
                    "如果你也{title}，请记住这一点",
                    "{title}的她，最终如何重获新生",
                    "每个{title}的女人，都该看看这个",
                ],
            },
            "skill": {  # 技术展示
                "teaching": [
                    "{title}，她练了{time}的完整教程",
                    "{title}，新手也能学会的3个步骤",
                    "她用{title}做到月入{income}，方法全在这",
                ],
                "showcase": [
                    "这就是{title}的实力，月入{income}不是梦",
                    "{title}的背后，是{time}的坚持",
                    "从0到{title}，她的{time}修炼之路",
                ],
            },
            "life": {  # 美好生活
                "lifestyle": [
                    "{title}，创业女人也可以很精致",
                    "左手事业右手生活：{title}的日常",
                    "月入{income}后，她终于实现了{title}",
                ],
            },
        }
        
        # IP关键词库（用于匹配和替换）
        self._ip_keywords = {
            "identity": ["宝妈", "妈妈", "女性", "女人", "姐妹"],
            "action": ["创业", "副业", "摆摊", "做馒头", "开店"],
            "result": ["月入3万", "月入5万", "月入过万", "年入百万", "财务自由"],
            "emotion": ["逆袭", "翻身", "独立", "自强", "重生"],
        }
    
    def rewrite_topic(
        self,
        original_title: str,
        ip_profile: Dict[str, Any],
        strategy: RewriteStrategy = RewriteStrategy.TEMPLATE_SMART
    ) -> RewriteResult:
        """
        改写话题标题
        
        Args:
            original_title: 原标题
            ip_profile: IP画像
            strategy: 改写策略
            
        Returns:
            改写结果
        """
        # 1. 分析内容类型
        content_type = classify_content_type(original_title)
        
        # 2. 提取IP关键词
        ip_keywords = self._extract_ip_keywords(ip_profile)
        
        # 3. 分析原标题结构
        title_analysis = self._analyze_title(original_title)
        
        # 4. 根据策略改写
        if strategy == RewriteStrategy.LLM_SEMANTIC:
            rewritten, quality = self._rewrite_with_llm(
                original_title, content_type, ip_keywords, title_analysis
            )
        elif strategy == RewriteStrategy.TEMPLATE_SMART:
            rewritten, quality = self._rewrite_with_smart_template(
                original_title, content_type, ip_keywords, title_analysis
            )
        else:
            rewritten, quality = self._rewrite_with_keyword_replace(
                original_title, ip_keywords
            )
        
        # 5. 评估改写质量
        quality_score = self._evaluate_rewrite_quality(
            original_title, rewritten, ip_keywords, content_type
        )
        
        # 6. 如果质量太低，使用内置库替代
        if quality_score < 0.5:
            logger.warning(f"Rewrite quality too low ({quality_score:.2f}), using fallback")
            rewritten = self._generate_fallback_title(content_type, ip_keywords)
            quality_score = 0.6
            reason = "质量不佳，使用智能生成标题"
        else:
            reason = f"基于{get_content_type_name(content_type)}类型智能改写"
        
        return RewriteResult(
            original_title=original_title,
            rewritten_title=rewritten,
            content_type=content_type,
            strategy=strategy,
            quality_score=quality_score,
            ip_keywords_matched=ip_keywords,
            reason=reason
        )
    
    def _extract_ip_keywords(self, ip_profile: Dict[str, Any]) -> List[str]:
        """从IP画像提取关键词"""
        keywords = []
        
        # 核心字段
        fields = [
            ip_profile.get("expertise", ""),
            ip_profile.get("content_direction", ""),
            ip_profile.get("target_audience", ""),
            ip_profile.get("product_service", ""),
        ]
        
        text = " ".join(fields)
        
        # 提取匹配的关键词
        for category, words in self._ip_keywords.items():
            for word in words:
                if word in text and word not in keywords:
                    keywords.append(word)
        
        # 如果没有匹配到，使用默认值
        if not keywords:
            keywords = ["宝妈", "创业", "月入3万"]
        
        return keywords[:5]
    
    def _analyze_title(self, title: str) -> Dict[str, Any]:
        """分析标题结构"""
        analysis = {
            "has_number": bool(re.search(r'\d+', title)),
            "has_money": any(kw in title for kw in ["月入", "年入", "万", "元"]),
            "has_time": any(kw in title for kw in ["年", "月", "天", "小时"]),
            "has_emotion": any(kw in title for kw in ["逆袭", "翻身", "成功", "失败"]),
            "is_question": "?" in title or "？" in title or "如何" in title,
            "is_list": any(kw in title for kw in ["3个", "5个", "几", "多"]),
        }
        
        # 提取数字
        numbers = re.findall(r'\d+\.?\d*', title)
        if numbers:
            analysis["extracted_number"] = numbers[0]
        
        return analysis
    
    def _rewrite_with_smart_template(
        self,
        original_title: str,
        content_type: str,
        ip_keywords: List[str],
        analysis: Dict[str, Any]
    ) -> Tuple[str, float]:
        """使用智能模板改写"""
        
        # 选择模板组
        templates = self._smart_templates.get(content_type, {})
        if not templates:
            templates = self._smart_templates["money"]
        
        # 根据标题特征选择具体模板
        if analysis.get("has_emotion"):
            template_group = templates.get("story", templates.get("high_engagement", []))
        elif analysis.get("is_question"):
            template_group = templates.get("tutorial", templates.get("teaching", []))
        else:
            template_group = templates.get("high_engagement", templates.get("showcase", []))
        
        if not template_group:
            template_group = ["{title}：{kw1}的创业启示"]
        
        # 选择第一个模板
        template = template_group[0]
        
        # 准备替换变量
        kw1 = ip_keywords[0] if len(ip_keywords) > 0 else "宝妈"
        kw2 = ip_keywords[1] if len(ip_keywords) > 1 else "创业"
        income = analysis.get("extracted_number", "3万") if analysis.get("has_money") else "3万"
        time_val = analysis.get("extracted_number", "6个月") if analysis.get("has_time") else "6个月"
        choice = "独立" if content_type == "emotion" else "创业"
        
        # 替换变量
        rewritten = template.format(
            title=original_title,
            kw1=kw1,
            kw2=kw2,
            income=income,
            time=time_val,
            choice=choice
        )
        
        # 评估质量
        quality = 0.7  # 模板改写基础分
        
        return rewritten, quality
    
    def _rewrite_with_llm(
        self,
        original_title: str,
        content_type: str,
        ip_keywords: List[str],
        analysis: Dict[str, Any]
    ) -> Tuple[str, float]:
        """使用LLM语义改写（需要接入AI服务）"""
        # TODO: 接入AI服务后实现
        # 目前回退到模板改写
        return self._rewrite_with_smart_template(
            original_title, content_type, ip_keywords, analysis
        )
    
    def _rewrite_with_keyword_replace(
        self,
        original_title: str,
        ip_keywords: List[str]
    ) -> Tuple[str, float]:
        """关键词替换（保底方案）"""
        # 这种是原系统的机械拼接，现在不推荐使用
        rewritten = f"{original_title}：{ip_keywords[0]}的创业启示"
        return rewritten, 0.4
    
    def _evaluate_rewrite_quality(
        self,
        original: str,
        rewritten: str,
        ip_keywords: List[str],
        content_type: str
    ) -> float:
        """评估改写质量"""
        score = 0.5  # 基础分
        
        # 1. 长度合理性（15-30字最佳）
        length = len(rewritten)
        if 15 <= length <= 35:
            score += 0.15
        elif 10 <= length < 15 or 35 < length <= 45:
            score += 0.05
        
        # 2. 包含IP关键词
        matched_keywords = [kw for kw in ip_keywords if kw in rewritten]
        score += len(matched_keywords) * 0.05
        
        # 3. 不包含原标题的无关信息（如"国足"等）
        # 简化为检查原标题的非通用词是否在改写后出现
        original_words = set(re.findall(r'[\u4e00-\u9fa5]{2,}', original))
        rewritten_words = set(re.findall(r'[\u4e00-\u9fa5]{2,}', rewritten))
        
        # 如果原标题大部分词还在，可能是简单拼接
        overlap = original_words & rewritten_words
        if len(overlap) / len(original_words) > 0.8:
            score -= 0.2  # 可能是简单拼接
        elif len(overlap) / len(original_words) < 0.3:
            score += 0.1  # 语义改写较彻底
        
        # 4. 爆款元素检测
        viral_elements = ["月入", "赚钱", "逆袭", "秘诀", "真相", "揭秘", "必看"]
        has_viral = any(elem in rewritten for elem in viral_elements)
        if has_viral:
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def _generate_fallback_title(self, content_type: str, ip_keywords: List[str]) -> str:
        """生成保底标题（当改写质量太低时）"""
        kw1 = ip_keywords[0] if ip_keywords else "宝妈"
        kw2 = ip_keywords[1] if len(ip_keywords) > 1 else "创业"
        
        fallback_templates = {
            "money": f"从0到月入3万：这个{kw1}的{kw2}方法太绝了",
            "emotion": f"从负债到逆袭：一个{kw1}如何用{kw2}重启人生",
            "skill": f"手艺变现金：她用{kw1}做到月入3万",
            "life": f"创业女人的精致生活：{kw1}也要有仪式感",
        }
        
        return fallback_templates.get(content_type, f"{kw1}的{kw2}故事")
    
    def batch_rewrite(
        self,
        topics: List[Dict[str, Any]],
        ip_profile: Dict[str, Any],
        min_quality: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        批量改写话题
        
        Args:
            topics: 话题列表
            ip_profile: IP画像
            min_quality: 最低质量阈值
            
        Returns:
            改写后的话题列表
        """
        results = []
        
        for topic in topics:
            original_title = topic.get("title", "")
            
            # 如果原标题已经符合IP定位，不改写
            if self._is_already_matched(original_title, ip_profile):
                topic["original_title"] = original_title
                topic["rewrite_strategy"] = "no_rewrite"
                topic["rewrite_quality"] = 1.0
                results.append(topic)
                continue
            
            # 改写
            rewrite_result = self.rewrite_topic(original_title, ip_profile)
            
            # 如果质量不达标，使用内置库替代
            if rewrite_result.quality_score < min_quality:
                logger.info(f"Low quality rewrite for '{original_title}', using builtin")
                # 这里可以调用内置库生成新标题
                rewrite_result.rewritten_title = self._generate_fallback_title(
                    rewrite_result.content_type,
                    rewrite_result.ip_keywords_matched
                )
                rewrite_result.quality_score = 0.7
            
            # 更新话题
            topic["original_title"] = original_title
            topic["title"] = rewrite_result.rewritten_title
            topic["content_type"] = rewrite_result.content_type
            topic["content_type_name"] = get_content_type_name(rewrite_result.content_type)
            topic["rewrite_strategy"] = rewrite_result.strategy.value
            topic["rewrite_quality"] = rewrite_result.quality_score
            topic["rewrite_reason"] = rewrite_result.reason
            
            results.append(topic)
        
        return results
    
    def _is_already_matched(self, title: str, ip_profile: Dict[str, Any]) -> bool:
        """检查标题是否已经符合IP定位"""
        ip_keywords = self._extract_ip_keywords(ip_profile)
        
        # 如果标题包含至少2个IP关键词，认为已经匹配
        matched = [kw for kw in ip_keywords if kw in title]
        return len(matched) >= 2


# 全局实例
_rewrite_service: Optional[TopicRewriteService] = None


def get_rewrite_service() -> TopicRewriteService:
    """获取改写服务实例"""
    global _rewrite_service
    if _rewrite_service is None:
        _rewrite_service = TopicRewriteService()
    return _rewrite_service
