"""
竞品内容解构服务
分析竞品内容的结构：钩子 → 叙事 → 情绪 → CTA
"""
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.services.ai_client import chat


class CompetitorStructure(BaseModel):
    """竞品内容结构分析结果"""
    hook: str  # 钩子类型
    hook_text: str  # 钩子原文
    structure: str  # 叙事结构
    emotion_curve: List[Dict[str, str]]  # 情绪曲线节点
    key_points: List[str]  # 核心观点
    cta: str  # 结尾行动号召
    word_count: int
    style_features: List[str]
    viral_elements: List[str]  # 爆款元素识别


# 钩子类型映射
HOOK_TYPES = {
    "counter_intuitive": "反常识",
    "pain_point": "痛点",
    "suspense": "悬念",
    "data": "数据",
    "controversy": "争议",
    "authority": "权威",
    "empathy": "共情",
}

# 叙事结构映射
STRUCTURE_TYPES = {
    "problem_solution": "问题→分析→解决",
    "comparison": "对比→结论",
    "story_insight": "故事→启示",
    "list": "清单→总结",
    "qa": "问答→延展",
    "timeline": "时间线→高潮",
}

# 爆款元素关键词
VIRAL_ELEMENT_KEYWORDS = {
    "cost": ["省钱", "性价比", "亏", "免费", "便宜", "花了", "成本", "预算"],
    "crowd": ["大家", "很多人", "都在", "你身边", "同龄人", "别人", "都"],
    "weird": ["奇怪", "没想到", "居然", "竟然", "颠覆", "反直觉", "意外"],
    "worst": ["最差", "踩坑", "后悔", "避坑", "教训", "毁掉", "糟糕"],
    "contrast": ["但是", "然而", "其实", "原来", "对比", "天壤之别", "差距"],
    "nostalgia": ["以前", "当年", "回忆", "曾经", "时光", "小时候", "青春"],
    "hormone": ["激动", "兴奋", "爽", "燃", "眼泪", "破防", "绷不住"],
    "top": ["第一", "最强", "顶级", "天花板", "巅峰", "最强", "冠军"],
}


def detect_viral_elements(text: str) -> List[str]:
    """检测文本中的爆款元素"""
    found = []
    text_lower = text.lower()
    for element, keywords in VIRAL_ELEMENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                if element not in found:
                    found.append(element)
                break
    return found[:3]


def detect_hook_type(text: str) -> tuple[str, str]:
    """检测开头钩子类型"""
    first_200 = text[:200].lower()
    
    # 反常识
    if any(kw in first_200 for kw in ["没想到", "居然", "竟然", "其实", "但是", "颠覆", "反直觉"]):
        return "counter_intuitive", "反常识/颠覆认知"
    
    # 痛点
    if any(kw in first_200 for kw in ["还在", "有没有", "为什么", "是不是", "困扰", "烦恼"]):
        return "pain_point", "痛点提问"
    
    # 数据
    if re.search(r'\d+[万分]|\d+%|[0-9]+\.', first_200):
        return "data", "数据/数字"
    
    # 悬念
    if any(kw in first_200 for kw in ["竟然", "居然", "你知道", "猜猜", "揭秘", "内幕"]):
        return "suspense", "悬念/揭秘"
    
    # 争议
    if any(kw in first_200 for kw in ["真的", "其实", "真相", "都错了", "被骗"]):
        return "controversy", "争议/反转"
    
    # 默认
    return "empathy", "共情开场"


def detect_structure_type(text: str) -> str:
    """检测叙事结构"""
    text_lower = text.lower()
    
    if "第一步" in text or "首先" in text or "第一点" in text:
        return "list"
    if "后来" in text or "结果" in text or "最后" in text:
        return "timeline"
    if "对比" in text or "但是" in text or "而" in text:
        return "comparison"
    if "我曾经" in text or "记得" in text or "故事" in text:
        return "story_insight"
    if "为什么" in text or "怎么" in text:
        return "qa"
    
    return "problem_solution"


def detect_cta_type(text: str) -> str:
    """检测结尾CTA类型"""
    text_lower = text.lower()
    
    if "关注" in text_lower or "点个赞" in text_lower or "收藏" in text_lower:
        return "interaction"
    if "有问题" in text_lower or "可以问" in text_lower or "评论区" in text_lower:
        return "question"
    if "赶紧" in text_lower or "马上" in text_lower or "点击" in text_lower:
        return "action"
    if "记得" in text_lower or "下次" in text_lower or "下期" in text_lower:
        return "follow_up"
    
    return "summary"


def analyze_competitor_structure(
    content: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    分析竞品内容结构
    
    Args:
        content: 竞品内容文本
        use_llm: 是否使用LLM深度分析
    
    Returns:
        结构化分析结果
    """
    if not content or len(content.strip()) < 50:
        return {
            "error": "内容太短，无法分析",
            "hook": "unknown",
            "structure": "unknown",
        }
    
    # 基础规则分析
    hook_type, hook_desc = detect_hook_type(content)
    structure_type = detect_structure_type(content)
    cta_type = detect_cta_type(content)
    viral_elements = detect_viral_elements(content)
    word_count = len(content)
    
    # 提取关键句子作为观点
    sentences = re.split(r'[。！？\n]', content)
    key_points = [s.strip() for s in sentences if 20 <= len(s.strip()) <= 100][:5]
    
    # 情绪曲线（简单规则）
    emotion_curve = []
    if "但是" in content or "然而" in content:
        emotion_curve.append({"position": "early", "type": "conflict", "text": "冲突/反转"})
    if "终于" in content or "结果" in content:
        emotion_curve.append({"position": "middle", "type": "tension", "text": "紧张期待"})
    if any(w in content for w in ["太好了", "激动", "兴奋", "爽"]):
        emotion_curve.append({"position": "end", "type": "positive", "text": "正向情绪"})
    
    # 风格特征（基础规则）
    style_features = []
    if word_count < 300:
        style_features.append("短平快")
    if "！" in content or "？？" in content:
        style_features.append("情绪化")
    if re.search(r'\d+', content):
        style_features.append("数据化")
    if any(w in content for w in ["我", "我们", "你"]):
        style_features.append("人格化")
    
    result = {
        "hook": hook_type,
        "hook_text": hook_desc,
        "structure": structure_type,
        "emotion_curve": emotion_curve,
        "key_points": key_points,
        "cta": cta_type,
        "word_count": word_count,
        "style_features": style_features,
        "viral_elements": viral_elements,
        "confidence": 0.7,  # 基础规则置信度
    }
    
    # 如果启用LLM，进行深度分析
    if use_llm:
        try:
            llm_result = _llm_deep_analysis(content)
            if llm_result:
                # 合并LLM结果，提升置信度
                result.update(llm_result)
                result["confidence"] = 0.9
        except Exception as e:
            result["llm_error"] = str(e)
    
    return result


def _llm_deep_analysis(content: str) -> Optional[Dict[str, Any]]:
    """LLM深度分析（可选）"""

    prompt = f"""分析以下短视频脚本的结构，返回严格JSON（不要markdown代码块）：

## 脚本内容
{content[:3000]}

## 输出JSON格式
{{
  "hook": "钩子类型（counter_intuitive/pain_point/suspense/data/controversy/empathy）",
  "hook_text": "钩子原文",
  "structure": "叙事结构（problem_solution/comparison/story_insight/list/qa/timeline）",
  "emotion_curve": [{{"position": "early/middle/end", "type": "情绪类型", "text": "描述"}}],
  "key_points": ["核心观点列表"],
  "cta": "结尾CTA类型（interaction/question/action/follow_up/summary）",
  "style_features": ["风格特征"],
  "viral_elements": ["爆款元素ID列表"]
}}"""
    
    try:
        result = chat([{"role": "user", "content": prompt}])
        if result:
            import json
            data = json.loads(result)
            return data
    except:
        pass
    
    return None


def extract_structure_summary(structure: Dict[str, Any]) -> str:
    """提取结构摘要供生成使用"""
    parts = []
    
    if structure.get("hook_text"):
        parts.append(f"钩子：{structure['hook_text']}")
    
    if structure.get("structure"):
        parts.append(f"结构：{STRUCTURE_TYPES.get(structure['structure'], structure['structure'])}")
    
    if structure.get("viral_elements"):
        parts.append(f"爆款元素：{', '.join(structure['viral_elements'])}")
    
    if structure.get("key_points"):
        parts.append(f"核心观点：{' | '.join(structure['key_points'][:2])}")
    
    return " | ".join(parts)
