"""爆款原创策略模板（从 docs/策略指令模板 收敛后的可部署版本）。"""

from __future__ import annotations

from typing import Dict


VIRAL_SCRIPT_TEMPLATE_MAP: Dict[str, Dict[str, str]] = {
    # 前端 scriptTemplate: process | knowledge | story | opinion
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
}


def get_viral_template(script_template: str) -> Dict[str, str]:
    key = (script_template or "opinion").strip().lower()
    return VIRAL_SCRIPT_TEMPLATE_MAP.get(key, VIRAL_SCRIPT_TEMPLATE_MAP["opinion"])

