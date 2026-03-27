"""
观点升维服务
对原观点进行升华：延伸、反转、落地
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.services.ai_client import chat


class ViewpointElevation(BaseModel):
    """观点升维结果"""
    original_viewpoint: str
    elevated_viewpoint: str
    new_angle: str
    evidence: List[str]
    action_items: List[str]
    reversal_viewpoint: Optional[str] = None


ELEVATION_SYSTEM_PROMPT = """你是一个内容策略专家，擅长对观点进行升华重构。

升维方法论：
1. 延伸：从个案到普遍规律，从现象到本质
2. 升华：从个人经验到行业洞察，从微观到宏观
3. 反转：提供反向视角，挑战常识
4. 落地：给出可执行的建议和行动

请基于原观点，结合素材，进行升维。"""


ELEVATION_USER_PROMPT = """## 原观点
{original_viewpoint}

## IP风格特征
{ip_style}

## IP相关素材
{ip_assets}

## 竞品结构参考（可选）
{structure_info}

请进行观点升维，输出严格JSON（不要markdown代码块）：
{{
  "elevated_viewpoint": "升华后的观点（一句话概括）",
  "new_angle": "新角度/新视角",
  "evidence": ["支撑论据1", "论据2", "论据3"],
  "action_items": ["可执行的行动建议1", "建议2"],
  "反转观点": "反向视角的观点（可选）"
}}"""


def elevate_viewpoint(
    original_viewpoint: str,
    ip_style: Dict[str, Any],
    ip_assets: str = "",
    structure_info: str = "",
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    对观点进行升维
    
    Args:
        original_viewpoint: 原始观点
        ip_style: IP风格特征
        ip_assets: IP相关素材
        structure_info: 竞品结构参考
        use_llm: 是否使用LLM
    
    Returns:
        升维后的观点
    """
    if not original_viewpoint or len(original_viewpoint.strip()) < 5:
        return {
            "error": "观点太短，无法升维",
            "elevated_viewpoint": original_viewpoint,
        }
    
    # 基础规则升维（无需LLM）
    basic_elevation = _rule_based_elevation(original_viewpoint)
    
    if use_llm:
        try:
            llm_result = _llm_elevate(
                original_viewpoint,
                ip_style,
                ip_assets,
                structure_info
            )
            if llm_result:
                # 合并结果
                return {
                    **basic_elevation,
                    **llm_result,
                    "method": "llm",
                }
        except Exception as e:
            basic_elevation["llm_error"] = str(e)
    
    basic_elevation["method"] = "rule"
    return basic_elevation


def _rule_based_elevation(viewpoint: str) -> Dict[str, Any]:
    """基于规则的简单升维"""
    
    # 检测观点类型
    is_comparison = "但是" in viewpoint or "而" in viewpoint or "对比" in viewpoint
    is_list = "第一" in viewpoint or "首先" in viewpoint or "其次" in viewpoint
    is_story = "我" in viewpoint or "曾经" in viewpoint or "记得" in viewpoint
    is_question = "？" in viewpoint or "为什么" in viewpoint or "怎么" in viewpoint
    
    # 升维规则
    elevated = viewpoint
    new_angle = ""
    action_items = []
    
    if is_comparison:
        new_angle = "从对比中找规律"
        action_items = ["提炼差异点", "归纳适用场景", "给出选择建议"]
    elif is_list:
        new_angle = "从清单中找核心"
        action_items = ["找出最关键的一点", "给出优先顺序", "补充注意事项"]
    elif is_story:
        new_angle = "从故事中提炼方法论"
        action_items = ["提取可复制的经验", "总结失败教训", "给出行动建议"]
    elif is_question:
        new_angle = "从问题中找本质"
        action_items = ["追根溯源", "给出解决方案", "提醒常见误区"]
    else:
        new_angle = "从观点中找洞察"
        action_items = ["补充数据支撑", "给出落地建议", "延伸相关话题"]
    
    return {
        "original_viewpoint": viewpoint,
        "elevated_viewpoint": f"【升维】{elevated}",
        "new_angle": new_angle,
        "evidence": ["基于观点类型的规则推导"],
        "action_items": action_items,
        "反转观点": _generate_reversal(viewpoint) if len(viewpoint) > 20 else None,
    }


def _generate_reversal(viewpoint: str) -> Optional[str]:
    """生成反转观点"""
    reversals = []
    
    if "要" in viewpoint:
        reversals.append(viewpoint.replace("要", "不要"))
    if "应该" in viewpoint:
        reversals.append(viewpoint.replace("应该", "不应该"))
    if "好" in viewpoint:
        reversals.append(viewpoint.replace("好", "不好"))
    if "对" in viewpoint:
        reversals.append(viewpoint.replace("对", "错"))
    
    if reversals:
        return f"【反转】{reversals[0]}"
    return None


def _llm_elevate(
    viewpoint: str,
    ip_style: Dict[str, Any],
    ip_assets: str,
    structure_info: str
) -> Optional[Dict[str, Any]]:
    """使用LLM进行观点升维"""
    
    style_str = f"IP名: {ip_style.get('name', '')}, 风格: {ip_style.get('style_features', '')}, 口头禅: {ip_style.get('catchphrases', '')}"
    
    prompt = ELEVATION_USER_PROMPT.format(
        original_viewpoint=viewpoint,
        ip_style=style_str,
        ip_assets=ip_assets[:1500] if ip_assets else "无",
        structure_info=structure_info[:500] if structure_info else "无"
    )
    
    try:
        result = chat(
            [{"role": "system", "content": ELEVATION_SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
        )
        
        if result:
            import json
            data = json.loads(result)
            return {
                "elevated_viewpoint": data.get("elevated_viewpoint", viewpoint),
                "new_angle": data.get("new_angle", ""),
                "evidence": data.get("evidence", []),
                "action_items": data.get("action_items", []),
                "反转观点": data.get("反转观点"),
            }
    except Exception as e:
        raise e
    
    return None


def batch_elevate(
    viewpoints: List[str],
    ip_style: Dict[str, Any],
    ip_assets: str = ""
) -> List[Dict[str, Any]]:
    """批量升维观点"""
    results = []
    for vp in viewpoints:
        result = elevate_viewpoint(vp, ip_style, ip_assets)
        results.append(result)
    return results


def extract_elevated_summary(elevation: Dict[str, Any]) -> str:
    """提取升维摘要供生成使用"""
    parts = []
    
    if elevation.get("elevated_viewpoint"):
        parts.append(f"升华观点：{elevation['elevated_viewpoint'][:60]}")
    
    if elevation.get("new_angle"):
        parts.append(f"新角度：{elevation['new_angle']}")
    
    if elevation.get("反转观点"):
        parts.append(f"反向视角：{elevation['反转观点'][:40]}")
    
    if elevation.get("action_items"):
        parts.append(f"行动建议：{', '.join(elevation['action_items'][:2])}")
    
    return " | ".join(parts)
