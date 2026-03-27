"""爆款原创策略模板（从 docs/策略指令模板 收敛后的可部署版本）。"""

from __future__ import annotations

from typing import Dict, Iterable, List


VIRAL_SCRIPT_TEMPLATE_MAP: Dict[str, Dict[str, str]] = {
    # 前端 scriptTemplate: process | knowledge | story | opinion | custom
    "process": {
        "name": "晒过程",
        "instruction": (
            "结构：3秒反常识/过程悬念钩子 -> 15-20秒过程三节奏（动作/卡点/突破）"
            " -> 5-8秒结果对比 -> 2秒互动CTA。"
            "优先使用：冲突反差、情绪共鸣、好奇缺口；少用恐惧诉求。"
        ),
    },
    "knowledge": {
        "name": "教知识",
        "instruction": (
            "结构：痛点钩子 -> 认知颠覆 -> 三步解决方案 -> 口诀总结 -> 转化CTA。"
            "每步必须可执行、可验证，术语要有“人话翻译”。"
            "优先使用：权威信任、利益承诺、认知反转。"
        ),
    },
    "story": {
        "name": "讲故事",
        "instruction": (
            "结构：情境钩子 -> 困境铺垫 -> 冲突升级 -> 高潮与方法论 -> 情感闭环CTA。"
            "必须有具体细节（时间/金额/行为/对话），先讲真实再讲结论。"
            "优先使用：情绪共鸣、冲突反差、好奇缺口。"
        ),
    },
    "opinion": {
        "name": "说观点",
        "instruction": (
            "结构：观点炸弹钩子 -> 双层论证 -> 情绪共振 -> 争议提问CTA。"
            "观点要有证据链（数据/案例/原理），避免空喊口号。"
            "优先使用：认知反转、冲突反差；可结合权威背书。"
        ),
    },
    "custom": {
        "name": "自定义",
        "instruction": (
            "无固定四大模板约束：在符合口播节奏与平台规范的前提下，"
            "严格按用户在「自定义结构说明」中给出的分段/镜头/时长意图组织全文；"
            "若用户未写结构说明，则结合选题与 IP 人设自行设计清晰起承转合，并保证有钩子与 CTA。"
        ),
    },
}

# 四大脚本 × 八大爆款（映射到前端元素ID：cost/crowd/weird/worst/contrast/nostalgia/hormone/top）
AUTO_VIRAL_ELEMENT_MAP: Dict[str, List[str]] = {
    # 反差 + 情绪共鸣（过程型更重真实与共情）
    "process": ["contrast", "nostalgia"],
    # 权威 + 利益 + 认知反转（知识型强调专业与可得收益）
    "knowledge": ["top", "cost", "contrast"],
    # 情绪 + 反差（故事型以情感牵引为主）
    "story": ["nostalgia", "contrast"],
    # 认知反转 + 冲突 + 热点感（观点型更重冲突与传播）
    "opinion": ["contrast", "top", "weird"],
    # 自定义：均衡组合，便于系统自动配元素时仍有多样爆款抓手
    "custom": ["contrast", "nostalgia", "top"],
}

VALID_VIRAL_ELEMENTS = {
    "cost",
    "crowd",
    "weird",
    "worst",
    "contrast",
    "nostalgia",
    "hormone",
    "top",
}


def get_viral_template(script_template: str) -> Dict[str, str]:
    key = (script_template or "opinion").strip().lower()
    if key == "custom":
        return VIRAL_SCRIPT_TEMPLATE_MAP["custom"]
    return VIRAL_SCRIPT_TEMPLATE_MAP.get(key, VIRAL_SCRIPT_TEMPLATE_MAP["opinion"])


def resolve_viral_elements(script_template: str, requested: Iterable[str] | None) -> List[str]:
    """
    解析最终使用的爆款元素：
    - 若用户未选、或选择了 auto/system_auto，则按脚本模板自动配置；
    - 否则使用用户手选（仅保留合法ID）。
    """
    req = [str(x).strip().lower() for x in (requested or []) if str(x).strip()]
    req = [x for x in req if x in VALID_VIRAL_ELEMENTS or x in {"auto", "system_auto"}]

    should_auto = (not req) or any(x in {"auto", "system_auto"} for x in req)
    if should_auto:
        key = (script_template or "opinion").strip().lower()
        auto = AUTO_VIRAL_ELEMENT_MAP.get(key, AUTO_VIRAL_ELEMENT_MAP["opinion"])
        return list(auto)

    # 去重保序
    out: List[str] = []
    for x in req:
        if x in VALID_VIRAL_ELEMENTS and x not in out:
            out.append(x)
    return out

