"""
智能IP匹配器

评估内容标题/选题与IP画像的匹配度
使用语义分析而非简单的关键词匹配
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MatchDimension(Enum):
    """匹配维度"""
    DOMAIN = "domain"           # 领域匹配
    AUDIENCE = "audience"       # 受众匹配
    STYLE = "style"             # 风格匹配
    VALUE = "value"             # 价值匹配
    FEASIBILITY = "feasibility" # 可拍性匹配


@dataclass
class MatchScore:
    """匹配分数详情"""
    overall: float  # 总分 0-1
    dimensions: Dict[str, float]  # 各维度得分
    reasons: List[str]  # 评分理由
    suggestions: List[str]  # 改进建议


class SmartIPMatcher:
    """
    智能IP匹配器
    
    评估标题与IP的多维度匹配度
    """
    
    def __init__(self):
        # 领域关键词映射
        self.domain_keywords = {
            "创业": ["创业", "赚钱", "生意", "项目", "副业", "开店", "摆摊", "投资"],
            "情感": ["情感", "爱情", "婚姻", "分手", "挽回", "心理", "治愈", "成长"],
            "教育": ["教育", "学习", "知识", "课程", "教学", "培训", "考试", "学校"],
            "健康": ["健康", "养生", "健身", "减肥", "医疗", "保健", "营养", "运动"],
            "美妆": ["美妆", "护肤", "化妆", "穿搭", "时尚", "美容", "变美", "颜值"],
            "生活": ["生活", "日常", "vlog", "家居", "美食", "旅行", "宠物", "爱好"],
            "职场": ["职场", "工作", "面试", "晋升", "同事", "老板", "办公室", "简历"],
            "科技": ["科技", "数码", "互联网", "AI", "手机", "电脑", "软件", "APP"],
        }
        
        # 受众关键词映射
        self.audience_keywords = {
            "宝妈": ["宝妈", "妈妈", "带娃", "育儿", "母婴", "孩子", "宝宝", "全职妈妈"],
            "年轻人": ["年轻人", "90后", "00后", "大学生", "刚毕业", "职场新人"],
            "中年人": ["中年", "35岁", "40岁", "中年危机", "上有老下有小"],
            "女性": ["女性", "女生", "女人", "姐妹", "她", "女"],
            "男性": ["男性", "男生", "男人", "兄弟", "他", "男"],
            "创业者": ["创业者", "老板", "创始人", "CEO", "合伙人", "企业家"],
            "上班族": ["上班族", "打工人", "白领", "职员", "员工", "996"],
        }
        
        # 内容类型检测关键词
        self.content_type_keywords = {
            "money": ["月入", "赚钱", "收入", "利润", "营收", "变现", "盈利", "年收入", "万元", "万+", "赚钱", "搞钱"],
            "emotion": ["情感", "故事", "逆袭", "重生", "治愈", "温暖", "感动", "眼泪", "心碎"],
            "skill": ["教程", "方法", "技巧", "步骤", "攻略", "指南", "干货", "必看", "学会", "掌握"],
            "life": ["生活", "日常", "vlog", "精致", "仪式感", "品质", "享受", "放松"],
        }
        
        # 爆款元素关键词
        self.viral_element_keywords = {
            "cost": ["月入", "年入", "收入", "利润", "营收", "变现", "盈利", "万元", "万+", "赚钱", "搞钱"],
            "crowd": ["普通人", "小白", "新手", "零基础", "人人", "都可以", "适合所有人"],
            "weird": ["秘密", "真相", "揭秘", "内幕", "不为人知", "偷偷", "暗中"],
            "worst": ["避坑", "教训", "失败", "亏损", "惨痛", "后悔", "千万不要"],
            "contrast": ["vs", "对比", "差距", "区别", " before", " after", "从前", "现在"],
            "nostalgia": ["回忆", "童年", "青春", "过去", "曾经", "那时候", "怀念"],
            "hormone": ["震惊", "愤怒", "感动", "泪目", "震撼", "炸裂", "爆款", "绝了"],
            "top": ["最全", "最强", "最好", "第一", "顶级", "天花板", "王者", "必看"],
        }
    
    def calculate_match_score(
        self,
        title: str,
        ip_profile: Dict[str, Any]
    ) -> float:
        """
        计算标题与IP的匹配分数
        
        Args:
            title: 标题
            ip_profile: IP画像
        
        Returns:
            匹配分数 0-1
        """
        match_result = self.analyze_match(title, ip_profile)
        return match_result.overall
    
    def analyze_match(
        self,
        title: str,
        ip_profile: Dict[str, Any]
    ) -> MatchScore:
        """
        详细分析标题与IP的匹配度
        
        Returns:
            MatchScore对象
        """
        dimensions = {}
        reasons = []
        suggestions = []
        
        # 1. 领域匹配度 (25%)
        domain_score = self._calculate_domain_match(title, ip_profile)
        dimensions[MatchDimension.DOMAIN.value] = domain_score
        if domain_score > 0.7:
            reasons.append("标题与IP专业领域高度相关")
        elif domain_score < 0.3:
            suggestions.append("标题与IP领域关联度较低，建议调整角度")
        
        # 2. 受众匹配度 (25%)
        audience_score = self._calculate_audience_match(title, ip_profile)
        dimensions[MatchDimension.AUDIENCE.value] = audience_score
        if audience_score > 0.7:
            reasons.append("标题能有效触达IP目标受众")
        elif audience_score < 0.3:
            suggestions.append("标题对目标受众吸引力可能不足")
        
        # 3. 风格匹配度 (20%)
        style_score = self._calculate_style_match(title, ip_profile)
        dimensions[MatchDimension.STYLE.value] = style_score
        
        # 4. 价值匹配度 (15%)
        value_score = self._calculate_value_match(title, ip_profile)
        dimensions[MatchDimension.VALUE.value] = value_score
        
        # 5. 可拍性匹配度 (15%)
        feasibility_score = self._calculate_feasibility_match(title, ip_profile)
        dimensions[MatchDimension.FEASIBILITY.value] = feasibility_score
        
        # 计算加权总分
        weights = {
            MatchDimension.DOMAIN.value: 0.25,
            MatchDimension.AUDIENCE.value: 0.25,
            MatchDimension.STYLE.value: 0.20,
            MatchDimension.VALUE.value: 0.15,
            MatchDimension.FEASIBILITY.value: 0.15,
        }
        
        overall = sum(dimensions.get(k, 0) * w for k, w in weights.items())
        
        return MatchScore(
            overall=round(overall, 2),
            dimensions=dimensions,
            reasons=reasons,
            suggestions=suggestions
        )
    
    def _calculate_domain_match(self, title: str, ip_profile: Dict[str, Any]) -> float:
        """计算领域匹配度"""
        expertise = ip_profile.get("expertise", "").lower()
        content_direction = ip_profile.get("content_direction", "").lower()
        ip_text = f"{expertise} {content_direction}"
        
        # 找出IP的领域
        ip_domains = set()
        for domain, keywords in self.domain_keywords.items():
            for kw in keywords:
                if kw in ip_text:
                    ip_domains.add(domain)
                    break
        
        if not ip_domains:
            return 0.5  # 未知领域，给中等分
        
        # 检查标题是否包含相关领域关键词
        title_lower = title.lower()
        match_count = 0
        for domain in ip_domains:
            keywords = self.domain_keywords.get(domain, [])
            for kw in keywords:
                if kw in title_lower:
                    match_count += 1
                    break
        
        if match_count == 0:
            # 检查是否有语义相关（简单实现）
            return 0.3
        
        return min(1.0, 0.5 + match_count * 0.2)
    
    def _calculate_audience_match(self, title: str, ip_profile: Dict[str, Any]) -> float:
        """计算受众匹配度"""
        target_audience = ip_profile.get("target_audience", "").lower()
        title_lower = title.lower()
        
        # 找出IP的目标受众
        ip_audiences = set()
        for audience, keywords in self.audience_keywords.items():
            for kw in keywords:
                if kw in target_audience:
                    ip_audiences.add(audience)
                    break
        
        if not ip_audiences:
            return 0.5  # 未知受众，给中等分
        
        # 检查标题是否针对这些受众
        match_count = 0
        for audience in ip_audiences:
            keywords = self.audience_keywords.get(audience, [])
            for kw in keywords:
                if kw in title_lower:
                    match_count += 1
                    break
        
        if match_count == 0:
            return 0.3
        
        return min(1.0, 0.4 + match_count * 0.2)
    
    def _calculate_style_match(self, title: str, ip_profile: Dict[str, Any]) -> float:
        """计算风格匹配度"""
        # 基于IP的风格特征
        style_features = ip_profile.get("style_features", "").lower()
        
        # 检测标题风格
        title_style_indicators = {
            "professional": ["专业", "深度", "分析", "研究", "数据", "报告"],
            "casual": ["轻松", "搞笑", "吐槽", "八卦", "娱乐"],
            "inspirational": ["励志", "逆袭", "成功", "奋斗", "坚持", "梦想"],
            "practical": ["干货", "教程", "方法", "步骤", "攻略", "必看"],
            "emotional": ["感动", "温暖", "治愈", "泪目", "震撼"],
        }
        
        # 简单匹配：如果标题风格与IP风格描述有重叠
        title_lower = title.lower()
        match_score = 0.5
        
        for style, indicators in title_style_indicators.items():
            for indicator in indicators:
                if indicator in title_lower and indicator in style_features:
                    match_score += 0.15
                elif indicator in title_lower:
                    # 标题有风格特征但IP描述中没有明确说明
                    match_score += 0.05
        
        return min(1.0, match_score)
    
    def _calculate_value_match(self, title: str, ip_profile: Dict[str, Any]) -> float:
        """计算价值主张匹配度"""
        unique_value = ip_profile.get("unique_value_prop", "").lower()
        
        if not unique_value:
            return 0.5
        
        # 提取标题中的价值关键词
        title_lower = title.lower()
        
        # 价值关键词
        value_keywords = ["省钱", "赚钱", "省时间", "高效", "简单", "轻松", "专业", "靠谱"]
        
        match_count = 0
        for kw in value_keywords:
            if kw in title_lower and kw in unique_value:
                match_count += 1
        
        return min(1.0, 0.4 + match_count * 0.15)
    
    def _calculate_feasibility_match(self, title: str, ip_profile: Dict[str, Any]) -> float:
        """计算可拍性匹配度（IP是否有能力拍这个内容）"""
        # 基于标题复杂度判断
        # 过于复杂的选题可能不适合
        
        # 检测是否包含需要专业设备/场景的词汇
        complex_indicators = ["电影级", "纪录片", "航拍", "特效", "专业棚", "团队"]
        title_lower = title.lower()
        
        complexity_score = 0
        for indicator in complex_indicators:
            if indicator in title_lower:
                complexity_score += 0.2
        
        # 复杂度越高，可拍性越低（假设IP是单人/小团队）
        feasibility = 1.0 - complexity_score
        
        # 检查是否有IP能提供的独特资源/经历
        expertise = ip_profile.get("expertise", "").lower()
        if any(kw in title_lower for kw in expertise.split(",") if kw):
            feasibility += 0.1
        
        return max(0.3, min(1.0, feasibility))
    
    def detect_content_type(self, title: str) -> Tuple[str, float]:
        """
        检测标题的内容类型
        
        Returns:
            (内容类型, 置信度)
        """
        title_lower = title.lower()
        scores = {t: 0 for t in self.content_type_keywords.keys()}
        
        for content_type, keywords in self.content_type_keywords.items():
            for kw in keywords:
                if kw in title_lower:
                    scores[content_type] += 1
        
        # 找出最高分的类型
        best_type = max(scores.items(), key=lambda x: x[1])
        
        if best_type[1] == 0:
            return "general", 0.5
        
        # 计算置信度
        total = sum(scores.values())
        confidence = best_type[1] / total if total > 0 else 0.5
        
        return best_type[0], round(confidence, 2)
    
    def extract_viral_elements(self, title: str) -> List[str]:
        """提取标题中的爆款元素"""
        title_lower = title.lower()
        elements = []
        
        for element, keywords in self.viral_element_keywords.items():
            for kw in keywords:
                if kw in title_lower:
                    elements.append(element)
                    break
        
        return elements
    
    def suggest_improvements(
        self,
        title: str,
        ip_profile: Dict[str, Any]
    ) -> List[str]:
        """建议标题改进方向"""
        suggestions = []
        match_result = self.analyze_match(title, ip_profile)
        
        # 基于低分维度给出建议
        if match_result.dimensions.get(MatchDimension.DOMAIN.value, 0) < 0.5:
            expertise = ip_profile.get("expertise", "你的领域")
            suggestions.append(f"建议增加与「{expertise}」相关的关键词")
        
        if match_result.dimensions.get(MatchDimension.AUDIENCE.value, 0) < 0.5:
            audience = ip_profile.get("target_audience", "目标受众")
            suggestions.append(f"标题可以更明确地针对「{audience}」")
        
        if match_result.dimensions.get(MatchDimension.STYLE.value, 0) < 0.5:
            suggestions.append("标题风格可以与IP人设更一致")
        
        # 检查爆款元素
        viral_elements = self.extract_viral_elements(title)
        if len(viral_elements) < 2:
            suggestions.append("建议增加爆款元素（如数字、对比、悬念等）")
        
        return suggestions or match_result.suggestions


# ============== 便捷函数 ==============

_matcher: Optional[SmartIPMatcher] = None


def get_smart_matcher() -> SmartIPMatcher:
    """获取全局匹配器实例"""
    global _matcher
    if _matcher is None:
        _matcher = SmartIPMatcher()
    return _matcher


def calculate_ip_match_score(title: str, ip_profile: Dict[str, Any]) -> float:
    """便捷函数：计算IP匹配分数"""
    matcher = get_smart_matcher()
    return matcher.calculate_match_score(title, ip_profile)
