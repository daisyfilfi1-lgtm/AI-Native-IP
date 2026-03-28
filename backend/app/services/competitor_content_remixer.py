"""
竞品内容重构引擎

核心思想：不是简单改写标题，而是重构内容的"内核"

重构流程：
1. 解构：分析竞品爆款的内容结构（钩子-冲突-解决方案-结果）
2. 提取：提取爆款的底层逻辑（情绪共鸣点、痛点、好奇点）
3. 重构：用IP的人设和经历重新包装这个内核
4. 验证：确保重构后的内容符合IP定位

示例：
竞品爆款："30岁被裁员后，我用这个方法月入5万"
- 钩子：数字+结果前置
- 冲突：被裁员（中年危机）
- 内核：低谷逆袭的励志故事
- 解决方案暗示：有方法可学

重构为IP（小敏-宝妈创业）：
"在家带娃3年没收入，我用这个副业方法月入3万"
- 钩子：同理（数字+结果）
- 冲突：带娃无收入（宝妈痛点）
- 内核：同样励志，但场景换成宝妈熟悉的
- 解决方案：副业方法（符合创业IP）
"""

import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ContentAngle(Enum):
    """内容角度类型"""
    TRANSFORMATION = "逆袭/转变"  # 从A到B的转变
    CONFESSION = "坦白/揭秘"      # 分享秘密/真相
    GUIDE = "教程/方法"           # 教你怎么做
    STORY = "故事/经历"           # 讲自己的故事
    COMPARISON = "对比/差距"      # 展示前后对比
    CHALLENGE = "挑战/测试"       # 做什么挑战


@dataclass
class ContentStructure:
    """内容结构分析结果"""
    angle: ContentAngle          # 内容角度
    hook_type: str              # 钩子类型
    conflict: str               # 冲突点
    emotion: str                # 情绪类型
    target_audience: str        # 目标受众
    core_value: str             # 核心价值（用户能获得什么）
    content_type: str           # money/emotion/skill/life
    

@dataclass
class RemixResult:
    """重构结果"""
    original_title: str         # 原标题
    remixed_title: str          # 重构后的标题
    structure: ContentStructure # 内容结构
    angle: ContentAngle         # 采用的角度
    confidence: float           # 重构置信度（0-1）
    reason: str                 # 重构理由


class CompetitorContentRemixer:
    """
    竞品内容重构引擎
    
    不是简单的关键词替换，而是深度的内容内核重构
    """
    
    def __init__(self):
        # IP人设模板库
        self.ip_angle_templates = {
            # 小敏IP的人设角度
            "xiaomin": {
                "identity": "在家创业宝妈",
                "pain_point": "带娃没有收入、家庭地位低、想证明自己",
                "transformation": "从手心向上到月入过万",
                "content_voice": "真诚分享、接地气、实操性强",
                "forbidden_words": ["裁员", "职场", "老板", "同事"],  # 职场相关词不适合宝妈IP
            }
        }
    
    def remix(
        self, 
        competitor_topic: Dict[str, Any], 
        ip_profile: Dict[str, Any]
    ) -> Optional[RemixResult]:
        """
        重构竞品内容为IP选题
        
        Args:
            competitor_topic: 竞品选题数据（含content_structure）
            ip_profile: IP画像
        
        Returns:
            RemixResult: 重构结果
        """
        original_title = competitor_topic.get("title", "")
        structure_data = competitor_topic.get("extra", {}).get("content_structure", {})
        
        if not original_title:
            return None
        
        # 1. 解析内容结构
        structure = self._parse_structure(structure_data, original_title)
        
        # 2. 检测是否适合重构
        if not self._is_remixable(structure, ip_profile):
            return None
        
        # 3. 选择重构角度
        angle = self._select_angle(structure, ip_profile)
        
        # 4. 执行重构
        remixed = self._execute_remix(original_title, structure, angle, ip_profile)
        
        if not remixed:
            return None
        
        # 5. 计算置信度
        confidence = self._calculate_confidence(structure, angle, ip_profile)
        
        return RemixResult(
            original_title=original_title,
            remixed_title=remixed,
            structure=structure,
            angle=angle,
            confidence=confidence,
            reason=f"基于竞品角度'{structure.angle.value}'重构，适配IP人设"
        )
    
    def _parse_structure(
        self, 
        structure_data: Dict[str, Any], 
        title: str
    ) -> ContentStructure:
        """解析内容结构"""
        # 从structure_data提取信息
        hook_type = structure_data.get("hook_type", "陈述")
        conflict = structure_data.get("conflict_point", "")
        emotion = structure_data.get("emotion_type", "中性")
        audience = structure_data.get("target_audience", "")
        
        # 推断内容角度
        angle = self._infer_angle(title, hook_type, conflict)
        
        # 推断核心价值
        core_value = self._extract_core_value(title)
        
        # 分类内容类型
        content_type = self._classify_content_type(title, emotion)
        
        return ContentStructure(
            angle=angle,
            hook_type=hook_type,
            conflict=conflict,
            emotion=emotion,
            target_audience=audience,
            core_value=core_value,
            content_type=content_type,
        )
    
    def _infer_angle(self, title: str, hook_type: str, conflict: str) -> ContentAngle:
        """推断内容角度"""
        title_lower = title.lower()
        
        # 逆袭/转变角度
        if any(w in title for w in ['从', '到', '逆袭', '转变', '变成', '成为']):
            return ContentAngle.TRANSFORMATION
        
        # 坦白/揭秘角度
        if any(w in title for w in ['坦白', '揭秘', '真相', '秘密', '没人告诉', '没人说']):
            return ContentAngle.CONFESSION
        
        # 教程/方法角度
        if any(w in title for w in ['方法', '技巧', '攻略', '教程', '步骤', '怎么做', '如何']):
            return ContentAngle.GUIDE
        
        # 对比角度
        if any(w in title for w in ['vs', '对比', '区别', '差距', 'before', 'after']):
            return ContentAngle.COMPARISON
        
        # 挑战角度
        if any(w in title for w in ['挑战', '测试', '尝试', '坚持', '天']):
            return ContentAngle.CHALLENGE
        
        # 默认故事角度
        return ContentAngle.STORY
    
    def _extract_core_value(self, title: str) -> str:
        """提取核心价值"""
        # 提取数字+结果
        patterns = [
            r'月入[\d万]+',
            r'[\d万]+粉丝',
            r'[\d万]+播放量',
            r'赚[\d万]+',
            r'省[\d万]+',
            r'[\d]+天',
        ]
        
        for pattern in patterns:
            import re
            match = re.search(pattern, title)
            if match:
                return match.group(0)
        
        # 提取方法/技巧类价值
        method_words = ['方法', '技巧', '攻略', '秘诀', '经验']
        for word in method_words:
            if word in title:
                return f"实用{word}"
        
        return "情绪共鸣"
    
    def _classify_content_type(self, title: str, emotion: str) -> str:
        """分类内容类型（4-3-2-1矩阵）"""
        # money类型
        if any(w in title for w in ['赚', '钱', '收入', '月入', '变现', '副业', '创业', '盈利', '成本', '价格']):
            return "money"
        
        # emotion类型
        if emotion in ['共鸣', '励志', '愤怒', '焦虑'] or any(w in title for w in ['感动', '心疼', '理解', '无奈']):
            return "emotion"
        
        # skill类型
        if any(w in title for w in ['方法', '技巧', '教程', '攻略', '步骤', '干货', '分享']):
            return "skill"
        
        # 默认life类型
        return "life"
    
    def _is_remixable(self, structure: ContentStructure, ip_profile: Dict[str, Any]) -> bool:
        """判断是否适合重构"""
        # 获取IP的禁忌词
        ip_id = ip_profile.get("ip_id", "")
        forbidden = self.ip_angle_templates.get(ip_id, {}).get("forbidden_words", [])
        
        # 检查冲突点是否包含禁忌词
        if structure.conflict in forbidden:
            return False
        
        # 检查内容角度是否适合
        # 某些角度可能不适合特定IP
        if structure.angle == ContentAngle.CHALLENGE and "宝妈" in str(ip_profile.get("expertise", "")):
            # 挑战类内容对宝妈可能不太实用
            pass  # 暂不拦截
        
        return True
    
    def _select_angle(
        self, 
        structure: ContentStructure, 
        ip_profile: Dict[str, Any]
    ) -> ContentAngle:
        """选择最适合的重构角度"""
        # 默认保持原角度
        return structure.angle
    
    def _execute_remix(
        self, 
        original_title: str, 
        structure: ContentStructure, 
        angle: ContentAngle,
        ip_profile: Dict[str, Any]
    ) -> Optional[str]:
        """
        执行内容重构
        
        这是核心逻辑：根据角度类型，用不同的重构策略
        """
        ip_id = ip_profile.get("ip_id", "xiaomin")  # 默认小敏
        ip_config = self.ip_angle_templates.get(ip_id, {})
        
        # 根据角度选择重构策略
        remixers = {
            ContentAngle.TRANSFORMATION: self._remix_transformation,
            ContentAngle.CONFESSION: self._remix_confession,
            ContentAngle.GUIDE: self._remix_guide,
            ContentAngle.STORY: self._remix_story,
            ContentAngle.COMPARISON: self._remix_comparison,
            ContentAngle.CHALLENGE: self._remix_challenge,
        }
        
        remixer = remixers.get(angle)
        if not remixer:
            return None
        
        return remixer(original_title, structure, ip_profile, ip_config)
    
    def _remix_transformation(
        self, 
        title: str, 
        structure: ContentStructure, 
        ip_profile: Dict[str, Any],
        ip_config: Dict[str, Any]
    ) -> str:
        """重构逆袭/转变类内容"""
        # 提取原内容的数字结果
        import re
        numbers = re.findall(r'(\d+[万千]?|[一二三四五六七八九十]+万?)', title)
        
        # 提取转变关键词
        transformation_keywords = ['从', '到', '变成', '成为', '逆袭', '翻身']
        
        # 构建新标题模板
        templates = [
            "在家带娃{time}没收入，我用这个方法{result}",
            "从手心向上到{result}，分享我的{period}创业经历",
            "{identity}如何{action}，实现{result}",
            "谁说{identity}不能{result}？我做到了",
        ]
        
        # 填充模板
        identity = ip_config.get("identity", "宝妈")
        time = "3年" if "3" in str(numbers) else "2年"
        result = numbers[0] + "收入" if numbers else "月入过万"
        period = "3年" if "3" in str(numbers) else "1年"
        action = "一边带娃一边赚钱"
        
        import random
        template = random.choice(templates)
        
        remixed = template.format(
            identity=identity,
            time=time,
            result=result,
            period=period,
            action=action
        )
        
        return remixed
    
    def _remix_confession(
        self, 
        title: str, 
        structure: ContentStructure, 
        ip_profile: Dict[str, Any],
        ip_config: Dict[str, Any]
    ) -> str:
        """重构坦白/揭秘类内容"""
        templates = [
            "{identity}坦白局：关于{topic}，没人告诉你的真相",
            "做{topic}{time}后，我发现这些{topic}都在骗人",
            "揭秘{topic}行业内幕，{identity}看完别踩坑",
            "写给{target}：{topic}的真相可能会让你失望",
        ]
        
        identity = ip_config.get("identity", "宝妈")
        topic = "副业" if "副业" in title or "创业" in title else "在家赚钱"
        time = "3年" 
        target = "想搞钱的宝妈"
        
        import random
        template = random.choice(templates)
        
        return template.format(
            identity=identity,
            topic=topic,
            time=time,
            target=target
        )
    
    def _remix_guide(
        self, 
        title: str, 
        structure: ContentStructure, 
        ip_profile: Dict[str, Any],
        ip_config: Dict[str, Any]
    ) -> str:
        """重构教程/方法类内容"""
        templates = [
            "{identity}必看：{topic}的{num}个{method}",
            "{result}后总结的{method}，{target}直接抄作业",
            "没{resource}没{resource2}？这个{method}让{identity}{result}",
            "从0到{result}，{identity}的{topic}{method}全分享",
        ]
        
        identity = ip_config.get("identity", "宝妈")
        topic = "在家赚钱" if "创业" in title else "搞副业"
        num = "3"
        method = "实用方法"
        result = "月入过万"
        target = "想赚钱的宝妈"
        resource = "本钱"
        resource2 = "人脉"
        
        import random
        template = random.choice(templates)
        
        return template.format(
            identity=identity,
            topic=topic,
            num=num,
            method=method,
            result=result,
            target=target,
            resource=resource,
            resource2=resource2
        )
    
    def _remix_story(
        self, 
        title: str, 
        structure: ContentStructure, 
        ip_profile: Dict[str, Any],
        ip_config: Dict[str, Any]
    ) -> str:
        """重构故事/经历类内容"""
        templates = [
            "{time}前，{conflict}的我{action}，现在{result}",
            "一个{identity}的{period}：从{before}到{after}",
            "那年我{age}，{conflict}，决定{action}",
            "{identity}自救指南：当{conflict}时，我{action}",
        ]
        
        identity = ip_config.get("identity", "宝妈")
        time = "3年"
        period = "3年创业史"
        conflict = structure.conflict or "没有收入"
        action = "开始在家做副业"
        result = "月入3万"
        before = "手心向上"
        after = "经济独立"
        age = "30岁"
        
        import random
        template = random.choice(templates)
        
        return template.format(
            identity=identity,
            time=time,
            period=period,
            conflict=conflict,
            action=action,
            result=result,
            before=before,
            after=after,
            age=age
        )
    
    def _remix_comparison(
        self, 
        title: str, 
        structure: ContentStructure, 
        ip_profile: Dict[str, Any],
        ip_config: Dict[str, Any]
    ) -> str:
        """重构对比类内容"""
        templates = [
            "{before} vs {after}：{identity}的{topic}对比",
            "同样是{identity}，为什么她{result1}而你{result2}？",
            "{topic}前 vs {topic}后：我的{change}太明显了",
        ]
        
        identity = ip_config.get("identity", "宝妈")
        before = "手心向上"
        after = "经济独立"
        topic = "搞副业"
        result1 = "月入3万"
        result2 = "还在焦虑"
        change = "变化"
        
        import random
        template = random.choice(templates)
        
        return template.format(
            identity=identity,
            before=before,
            after=after,
            topic=topic,
            result1=result1,
            result2=result2,
            change=change
        )
    
    def _remix_challenge(
        self, 
        title: str, 
        structure: ContentStructure, 
        ip_profile: Dict[str, Any],
        ip_config: Dict[str, Any]
    ) -> str:
        """重构挑战类内容"""
        templates = [
            "挑战{action}{time}：{identity}的{topic}实验",
            "{time}挑战：{action}后，{result}",
            "我用{time}证明：{identity}也能{action}",
        ]
        
        identity = ip_config.get("identity", "宝妈")
        action = "在家搞副业"
        time = "30天"
        topic = "赚钱"
        result = "我做到了"
        
        import random
        template = random.choice(templates)
        
        return template.format(
            identity=identity,
            action=action,
            time=time,
            topic=topic,
            result=result
        )
    
    def _calculate_confidence(
        self, 
        structure: ContentStructure, 
        angle: ContentAngle,
        ip_profile: Dict[str, Any]
    ) -> float:
        """计算重构置信度"""
        confidence = 0.7  # 基础分
        
        # 有明确内容角度加分
        if structure.angle != ContentAngle.STORY:
            confidence += 0.1
        
        # 有冲突点加分
        if structure.conflict:
            confidence += 0.1
        
        # 有明确受众加分
        if structure.target_audience:
            confidence += 0.1
        
        return min(1.0, confidence)


# 便捷函数
def remix_competitor_topic(
    competitor_topic: Dict[str, Any], 
    ip_profile: Dict[str, Any]
) -> Optional[RemixResult]:
    """便捷函数：重构单个竞品选题"""
    remixer = CompetitorContentRemixer()
    return remixer.remix(competitor_topic, ip_profile)
