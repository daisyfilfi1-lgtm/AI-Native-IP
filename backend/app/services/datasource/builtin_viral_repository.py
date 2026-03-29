"""
内置爆款库

当所有外部API失败时，提供按IP类型预设的高质量爆款标题
这些数据基于对多个平台热门内容的分析和提炼
"""

import logging
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.services.datasource.base import TopicData

logger = logging.getLogger(__name__)


class IPType(Enum):
    """IP类型分类"""
    MOM_ENTREPRENEUR = "mom_entrepreneur"      # 宝妈创业
    SIDE_HUSTLE = "side_hustle"                 # 副业赚钱
    KNOWLEDGE_PAID = "knowledge_paid"          # 知识付费
    LIFESTYLE = "lifestyle"                     # 生活方式
    EMOTIONAL = "emotional"                     # 情感成长
    SKILL_TEACHING = "skill_teaching"          # 技能教学
    GENERAL = "general"                         # 通用型


@dataclass
class ViralTemplate:
    """爆款标题模板"""
    title: str
    content_type: str  # money/emotion/skill/life
    viral_elements: List[str]  # 爆款元素
    target_audience: List[str]  # 目标受众标签
    applicable_ip_types: List[IPType]  # 适用的IP类型
    score: float = 4.5  # 爆款潜力分 0-5


class BuiltinViralRepository:
    """
    内置爆款库
    
    提供高质量的预设爆款标题，按IP类型分类
    当外部API全部失败时作为兜底方案
    """
    
    def __init__(self):
        self._templates: List[ViralTemplate] = []
        self._init_templates()
    
    def _init_templates(self):
        """初始化爆款模板库"""
        
        # ========== 宝妈创业类 (Mom Entrepreneur) ==========
        mom_templates = [
            # 搞钱方法论 (money)
            ViralTemplate(
                title="从0到月入3万：这个宝妈的副业方法太绝了",
                content_type="money",
                viral_elements=["cost", "crowd", "contrast"],
                target_audience=["宝妈", "创业女性", "想赚钱的人"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR, IPType.SIDE_HUSTLE],
                score=4.9
            ),
            ViralTemplate(
                title="带娃赚钱两不误：宝妈副业月入过万的3个秘诀",
                content_type="money",
                viral_elements=["tutorial", "cost", "crowd"],
                target_audience=["宝妈", "全职妈妈"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR],
                score=4.8
            ),
            ViralTemplate(
                title="35岁被裁后，我靠这个月入5万：宝妈逆袭实录",
                content_type="money",
                viral_elements=["contrast", "story", "cost"],
                target_audience=["35岁+女性", "失业人群", "宝妈"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR, IPType.SIDE_HUSTLE],
                score=4.9
            ),
            ViralTemplate(
                title="不需要本钱的生意：宝妈在家就能做的6个项目",
                content_type="money",
                viral_elements=["tutorial", "cost", "weird"],
                target_audience=["宝妈", "零本钱创业者"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR, IPType.SIDE_HUSTLE],
                score=4.7
            ),
            ViralTemplate(
                title="摆摊到开店：一个馒头宝妈的年入百万之路",
                content_type="money",
                viral_elements=["story", "cost", "contrast"],
                target_audience=["小生意人", "宝妈", "创业者"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR],
                score=4.8
            ),
            
            # 情感共情 (emotion)
            ViralTemplate(
                title="从负债50万到财务自由：一个宝妈的重生故事",
                content_type="emotion",
                viral_elements=["story", "contrast", "nostalgia"],
                target_audience=["负债人群", "宝妈", "想翻身的人"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR, IPType.EMOTIONAL],
                score=4.9
            ),
            ViralTemplate(
                title="老公不支持我创业，我用结果让他闭嘴",
                content_type="emotion",
                viral_elements=["conflict", "story", "hormone"],
                target_audience=["宝妈", "创业女性", "婚姻中的女性"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR, IPType.EMOTIONAL],
                score=4.7
            ),
            ViralTemplate(
                title="别人问我为什么那么拼：因为我不再相信婚姻",
                content_type="emotion",
                viral_elements=["story", "hormone", "contrast"],
                target_audience=["独立女性", "宝妈", "情感困惑者"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR, IPType.EMOTIONAL],
                score=4.6
            ),
            
            # 技能展示 (skill)
            ViralTemplate(
                title="手把手教你：宝妈如何从零开始做小红书",
                content_type="skill",
                viral_elements=["tutorial", "top", "crowd"],
                target_audience=["宝妈", "自媒体新手"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR, IPType.SKILL_TEACHING],
                score=4.7
            ),
            ViralTemplate(
                title="副业避坑指南：我花10万买来的教训",
                content_type="skill",
                viral_elements=["tutorial", "worst", "cost"],
                target_audience=["副业人群", "创业者"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR, IPType.SIDE_HUSTLE],
                score=4.8
            ),
            
            # 美好生活 (life)
            ViralTemplate(
                title="月入5万后，我终于可以给孩子买想要的东西了",
                content_type="life",
                viral_elements=["story", "cost", "nostalgia"],
                target_audience=["宝妈", "想改善生活的人"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR, IPType.LIFESTYLE],
                score=4.6
            ),
            ViralTemplate(
                title="创业宝妈的日常：左手事业右手家庭",
                content_type="life",
                viral_elements=["lifestyle", "contrast", "nostalgia"],
                target_audience=["宝妈", "创业女性"],
                applicable_ip_types=[IPType.MOM_ENTREPRENEUR, IPType.LIFESTYLE],
                score=4.5
            ),
        ]
        
        # ========== 副业赚钱类 (Side Hustle) ==========
        side_hustle_templates = [
            ViralTemplate(
                title="每天2小时，月入5位数：打工人必看的副业指南",
                content_type="money",
                viral_elements=["tutorial", "cost", "time"],
                target_audience=["打工人", "上班族", "想副业的人"],
                applicable_ip_types=[IPType.SIDE_HUSTLE, IPType.GENERAL],
                score=4.9
            ),
            ViralTemplate(
                title="下班后别刷手机了！这5个副业让你收入翻倍",
                content_type="money",
                viral_elements=["tutorial", "cost", "contrast"],
                target_audience=["上班族", "打工人"],
                applicable_ip_types=[IPType.SIDE_HUSTLE],
                score=4.8
            ),
            ViralTemplate(
                title="从月薪3000到月入3万：我的副业进化史",
                content_type="money",
                viral_elements=["story", "cost", "contrast"],
                target_audience=["低收入人群", "想赚钱的人"],
                applicable_ip_types=[IPType.SIDE_HUSTLE, IPType.GENERAL],
                score=4.9
            ),
            ViralTemplate(
                title="不需要辞职就能做的副业：我是如何兼顾主业的",
                content_type="money",
                viral_elements=["tutorial", "crowd", "time"],
                target_audience=["上班族", "想安全副业的人"],
                applicable_ip_types=[IPType.SIDE_HUSTLE],
                score=4.7
            ),
            ViralTemplate(
                title="副业收入超过主业后，我做出了这个选择",
                content_type="emotion",
                viral_elements=["story", "contrast", "decision"],
                target_audience=["副业成功者", "想转型的人"],
                applicable_ip_types=[IPType.SIDE_HUSTLE],
                score=4.6
            ),
        ]
        
        # ========== 知识付费类 (Knowledge Paid) ==========
        knowledge_templates = [
            ViralTemplate(
                title="知识变现的完整路径：从0到年入百万的实操方法",
                content_type="money",
                viral_elements=["tutorial", "cost", "top"],
                target_audience=["知识工作者", "专业人士"],
                applicable_ip_types=[IPType.KNOWLEDGE_PAID, IPType.SKILL_TEACHING],
                score=4.8
            ),
            ViralTemplate(
                title="为什么你的课程卖不出去？90%的人踩了这些坑",
                content_type="skill",
                viral_elements=["tutorial", "worst", "crowd"],
                target_audience=["知识付费从业者", "讲师"],
                applicable_ip_types=[IPType.KNOWLEDGE_PAID],
                score=4.7
            ),
            ViralTemplate(
                title="一条视频卖出100万课程：知识博主的核心打法",
                content_type="skill",
                viral_elements=["tutorial", "cost", "top"],
                target_audience=["知识博主", "想变现的人"],
                applicable_ip_types=[IPType.KNOWLEDGE_PAID],
                score=4.8
            ),
        ]
        
        # ========== 生活方式类 (Lifestyle) ==========
        lifestyle_templates = [
            ViralTemplate(
                title="月入过万后的生活：我终于活成了想要的样子",
                content_type="life",
                viral_elements=["story", "cost", "lifestyle"],
                target_audience=["想改善生活的人", "年轻人"],
                applicable_ip_types=[IPType.LIFESTYLE, IPType.GENERAL],
                score=4.6
            ),
            ViralTemplate(
                title="有钱人的快乐你想象不到：财务自由后的日常",
                content_type="life",
                viral_elements=["lifestyle", "cost", "contrast"],
                target_audience=["向往财务自由的人"],
                applicable_ip_types=[IPType.LIFESTYLE],
                score=4.5
            ),
        ]
        
        # ========== 情感成长类 (Emotional) ==========
        emotional_templates = [
            ViralTemplate(
                title="女人经济独立后，爱情都变得简单了",
                content_type="emotion",
                viral_elements=["hormone", "contrast", "story"],
                target_audience=["女性", "独立女性"],
                applicable_ip_types=[IPType.EMOTIONAL, IPType.GENERAL],
                score=4.7
            ),
            ViralTemplate(
                title="被背叛后的重生：我如何用事业治愈自己",
                content_type="emotion",
                viral_elements=["story", "contrast", "hormone"],
                target_audience=["情感受挫者", "想独立的女性"],
                applicable_ip_types=[IPType.EMOTIONAL],
                score=4.6
            ),
        ]
        
        # ========== 通用型 (General) ==========
        general_templates = [
            ViralTemplate(
                title="普通人逆袭的唯一路径：我花了5年才悟出的道理",
                content_type="emotion",
                viral_elements=["story", "contrast", "top"],
                target_audience=["普通人", "想逆袭的人"],
                applicable_ip_types=[IPType.GENERAL],
                score=4.8
            ),
            ViralTemplate(
                title="穷人的思维vs富人的思维：这一个区别决定了命运",
                content_type="skill",
                viral_elements=["contrast", "tutorial", "top"],
                target_audience=["想改变的人", "普通人"],
                applicable_ip_types=[IPType.GENERAL],
                score=4.7
            ),
            ViralTemplate(
                title="30岁前必须明白的3个道理：让你少走10年弯路",
                content_type="skill",
                viral_elements=["tutorial", "time", "top"],
                target_audience=["年轻人", "职场新人"],
                applicable_ip_types=[IPType.GENERAL],
                score=4.6
            ),
            ViralTemplate(
                title="那些成功的人，都在偷偷做这件事",
                content_type="skill",
                viral_elements=["weird", "tutorial", "top"],
                target_audience=["想成功的人", "普通人"],
                applicable_ip_types=[IPType.GENERAL],
                score=4.5
            ),
            ViralTemplate(
                title="为什么你那么努力却还是穷？真相可能会刺痛你",
                content_type="emotion",
                viral_elements=["contrast", "hormone", "story"],
                target_audience=["努力但没有结果的人"],
                applicable_ip_types=[IPType.GENERAL],
                score=4.7
            ),
        ]
        
        # 合并所有模板
        self._templates = (
            mom_templates +
            side_hustle_templates +
            knowledge_templates +
            lifestyle_templates +
            emotional_templates +
            general_templates
        )
        
        logger.info(f"[BuiltinViral] Initialized with {len(self._templates)} templates")
    
    def detect_ip_type(self, ip_profile: Dict[str, Any]) -> List[IPType]:
        """
        根据IP画像检测IP类型
        
        Returns:
            按匹配度排序的IP类型列表
        """
        scores = {ip_type: 0 for ip_type in IPType}
        
        expertise = ip_profile.get("expertise", "").lower()
        content_direction = ip_profile.get("content_direction", "").lower()
        target_audience = ip_profile.get("target_audience", "").lower()
        combined_text = f"{expertise} {content_direction} {target_audience}"
        
        # 关键词映射
        keywords_map = {
            IPType.MOM_ENTREPRENEUR: ["宝妈", "妈妈", "带娃", "母婴", "育儿"],
            IPType.SIDE_HUSTLE: ["副业", "兼职", "下班后", "上班族", "打工人"],
            IPType.KNOWLEDGE_PAID: ["知识", "课程", "讲师", "培训", "教育"],
            IPType.LIFESTYLE: ["生活", "日常", "vlog", "精致", "品质"],
            IPType.EMOTIONAL: ["情感", "成长", "心理", "治愈", "独立"],
            IPType.SKILL_TEACHING: ["教学", "教程", "技能", "学习", "方法"],
        }
        
        # 计算各类型得分
        for ip_type, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in combined_text:
                    scores[ip_type] += 1
        
        # 按得分排序
        sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # 返回得分大于0的类型，如果没有则返回GENERAL
        result = [ip_type for ip_type, score in sorted_types if score > 0]
        if not result:
            result = [IPType.GENERAL]
        
        return result
    
    def get_topics_for_ip(
        self,
        ip_profile: Dict[str, Any],
        limit: int = 12,
        content_type_distribution: Optional[Dict[str, float]] = None
    ) -> List[TopicData]:
        """
        获取适合IP的爆款选题
        
        Args:
            ip_profile: IP画像
            limit: 返回数量
            content_type_distribution: 内容类型分布 (money/emotion/skill/life)
        
        Returns:
            TopicData列表
        """
        # 1. 检测IP类型
        ip_types = self.detect_ip_type(ip_profile)
        logger.info(f"[BuiltinViral] Detected IP types: {[t.value for t in ip_types]}")
        
        # 2. 筛选匹配的模板
        matched_templates = []
        for template in self._templates:
            # 检查IP类型匹配
            if any(ip_type in template.applicable_ip_types for ip_type in ip_types):
                matched_templates.append(template)
        
        # 3. 按分数排序
        matched_templates.sort(key=lambda x: x.score, reverse=True)
        
        # 4. 按内容类型分布筛选
        distribution = content_type_distribution or {
            "money": 0.40,
            "emotion": 0.30,
            "skill": 0.20,
            "life": 0.10,
        }
        
        result = []
        for content_type, ratio in distribution.items():
            count = int(limit * ratio) + 1  # 多取一点，避免不够
            type_templates = [t for t in matched_templates if t.content_type == content_type]
            result.extend(type_templates[:count])
        
        # 5. 随机打乱，避免同一类型集中
        random.shuffle(result)
        
        # 6. 转换为TopicData
        topics = []
        for i, template in enumerate(result[:limit]):
            topic = TopicData(
                id=f"builtin_{template.content_type}_{i}",
                title=template.title,
                original_title=template.title,
                platform="builtin",
                url="",  # 内置库没有具体URL
                tags=template.viral_elements + ["内置爆款"],
                score=template.score,  # 使用模板分数
                source="builtin_viral",
                extra={
                    "content_type": template.content_type,
                    "viral_elements": template.viral_elements,
                    "target_audience": template.target_audience,
                    "is_builtin": True,
                    "builtin_score": template.score,
                }
            )
            topics.append(topic)
        
        logger.info(f"[BuiltinViral] Returning {len(topics)} builtin topics for IP")
        return topics
    
    def get_templates_by_content_type(self, content_type: str) -> List[ViralTemplate]:
        """获取指定内容类型的所有模板"""
        return [t for t in self._templates if t.content_type == content_type]
    
    def get_all_templates(self) -> List[ViralTemplate]:
        """获取所有模板"""
        return self._templates.copy()
    
    def add_custom_template(self, template: ViralTemplate):
        """添加自定义模板"""
        self._templates.append(template)
        logger.info(f"[BuiltinViral] Added custom template: {template.title[:30]}...")


# ============== 便捷函数 ==============

_repository: Optional[BuiltinViralRepository] = None


def get_builtin_repository() -> BuiltinViralRepository:
    """获取全局内置库实例"""
    global _repository
    if _repository is None:
        _repository = BuiltinViralRepository()
    return _repository


def get_builtin_topics(
    ip_profile: Dict[str, Any],
    limit: int = 12
) -> List[TopicData]:
    """便捷函数：获取内置爆款选题"""
    repo = get_builtin_repository()
    return repo.get_topics_for_ip(ip_profile, limit)
