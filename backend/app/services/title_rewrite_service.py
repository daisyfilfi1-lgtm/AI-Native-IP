"""
环节3：爆款标题 + IP → 改写标题

基于提取的爆款标题结构，结合IP人设生成改写标题。
核心：保留爆款结构，替换为IP视角和内容
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import IP
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class RewriteResult:
    """改写结果 - 包含语义分析"""
    original_title: str
    original_hook: str
    original_body: str
    
    # 改写版本
    rewritten_title: str
    rewritten_hook: str
    rewritten_body: str
    
    # 改写策略说明
    strategy: str
    
    # 元数据
    ip_id: str
    ip_name: str
    content_type: str
    
    # 状态
    success: bool
    
    # 可选字段（有默认值）
    analysis: str = ""  # 语义分析（LLM提供）
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "error": self.error,
            "original": {
                "title": self.original_title,
                "hook": self.original_hook,
                "body": self.original_body
            },
            "rewritten": {
                "title": self.rewritten_title,
                "hook": self.rewritten_hook,
                "body": self.rewritten_body
            },
            "analysis": self.analysis,
            "strategy": self.strategy,
            "ip_id": self.ip_id,
            "ip_name": self.ip_name,
            "content_type": self.content_type
        }


class TitleRewriteService:
    """
    标题改写服务
    
    核心逻辑：
    1. 分析爆款标题的hook结构（数字/身份/对比等）
    2. 提取IP的关键人设元素
    3. 使用AI将爆款结构IP化
    """
    
    async def rewrite(
        self,
        ip_id: str,
        original_title: str,
        original_hook: str,
        original_body: str,
        tags: List[str],
        content_type: str,
        strategy: str = "structure_keep"  # structure_keep, emotion_shift, angle_flip
    ) -> RewriteResult:
        """
        改写标题
        
        Args:
            ip_id: IP ID
            original_title: 原始爆款标题
            original_hook: 原始hook
            original_body: 原始body
            tags: 标签列表
            content_type: 内容类型
            strategy: 改写策略
        """
        # 获取IP信息
        db = SessionLocal()
        try:
            ip = db.query(IP).filter(IP.ip_id == ip_id).first()
            if not ip:
                return RewriteResult(
                    original_title=original_title,
                    original_hook=original_hook,
                    original_body=original_body,
                    rewritten_title="",
                    rewritten_hook="",
                    rewritten_body="",
                    strategy=strategy,
                    ip_id=ip_id,
                    ip_name="",
                    content_type=content_type,
                    success=False,
                    error=f"IP not found: {ip_id}"
                )
            
            # 提取IP人设信息
            ip_profile = self._extract_ip_profile(ip)
            
            # 构建prompt
            prompt = self._build_rewrite_prompt(
                ip_profile=ip_profile,
                original_title=original_title,
                original_hook=original_hook,
                original_body=original_body,
                tags=tags,
                content_type=content_type,
                strategy=strategy
            )
            
            # 调用AI改写
            try:
                from app.services.ai_client import chat
                
                messages = [
                    {"role": "system", "content": "你是一个专业的短视频标题改写专家，擅长分析爆款标题的结构并改写成符合特定IP人设的版本。"},
                    {"role": "user", "content": prompt}
                ]
                
                response = chat(messages, temperature=0.8)
                
                if response:
                    # 解析AI响应
                    rewritten = self._parse_ai_response(response)
                    
                    return RewriteResult(
                        original_title=original_title,
                        original_hook=original_hook,
                        original_body=original_body,
                        rewritten_title=rewritten["title"],
                        rewritten_hook=rewritten["hook"],
                        rewritten_body=rewritten["body"],
                        analysis=rewritten.get("analysis", ""),
                        strategy=f"ai_{strategy}",
                        ip_id=ip_id,
                        ip_name=ip.name,
                        content_type=content_type,
                        success=True
                    )
                else:
                    raise Exception("LLM returned empty response")
                
            except Exception as e:
                logger.error(f"AI rewrite failed: {e}")
                # 降级：使用规则改写
                return self._rule_based_rewrite(
                    ip_profile=ip_profile,
                    original_title=original_title,
                    original_hook=original_hook,
                    original_body=original_body,
                    content_type=content_type
                )
                
        finally:
            db.close()
    
    def _extract_ip_profile(self, ip: IP) -> Dict[str, Any]:
        """提取IP人设信息"""
        profile = {
            "name": ip.name,
            "nickname": ip.nickname or ip.name,
            "bio": ip.bio or "",
            "expertise": ip.expertise or "",
            "passion": ip.passion or "",
            "content_direction": ip.content_direction or "",
            "target_audience": ip.target_audience or "",
            "unique_value_prop": ip.unique_value_prop or "",
            "product_service": ip.product_service or "",
            "price_range": ip.price_range or "",
        }
        
        # 从style_profile提取风格信息
        if ip.style_profile:
            profile["style"] = {
                "tone": ip.style_profile.get("tone", []),
                "vocabulary": ip.style_profile.get("vocabulary", []),
                "sentence_patterns": ip.style_profile.get("sentence_patterns", []),
            }
        
        return profile
    
    def _build_rewrite_prompt(
        self,
        ip_profile: Dict[str, Any],
        original_title: str,
        original_hook: str,
        original_body: str,
        tags: List[str],
        content_type: str,
        strategy: str
    ) -> str:
        """构建语义改写prompt - 真正的LLM语义级改写"""
        
        strategy_desc = {
            "structure_keep": "深度理解原标题的吸引力要素，用IP视角重新表达",
            "emotion_shift": "转换情绪角度，如从焦虑/愤怒转为希望/温暖",
            "angle_flip": "反转观点角度，如从避坑/批评转为推荐/赞美"
        }.get(strategy, "深度理解原标题的吸引力要素，用IP视角重新表达")
        
        # 提取风格信息
        style_info = ""
        if ip_profile.get("style"):
            style = ip_profile["style"]
            if style.get("tone"):
                style_info += f"\n- 语气风格: {', '.join(style['tone'])}"
            if style.get("vocabulary"):
                style_info += f"\n- 常用词汇: {', '.join(style['vocabulary'][:5])}"
        
        prompt = f"""你是一个顶级的短视频文案创作者。你的任务是对爆款标题进行**语义级深度改写**——不是简单的关键词替换，而是理解原标题为什么能火，然后用IP的独特视角和语言风格重新创造。

## 第一步：分析原标题的爆款逻辑
请分析"{original_title}"为什么能火：
1. **核心吸引力**：它抓住了什么痛点/欲望/好奇心？
2. **结构要素**：数字？身份标签？对比？悬念？结果展示？
3. **情绪触发**：焦虑？希望？愤怒？好奇？共鸣？
4. **受众心理**：读者看到后会想什么？

## 第二步：IP人设画像
- **IP名称**: {ip_profile['name']}
- **昵称**: {ip_profile['nickname']}
- **简介**: {ip_profile['bio']}
- **擅长领域**: {ip_profile['expertise']}
- **热爱领域**: {ip_profile['passion']}
- **内容方向**: {ip_profile['content_direction']}
- **目标受众**: {ip_profile['target_audience']}
- **独特价值主张**: {ip_profile['unique_value_prop']}
- **产品/服务**: {ip_profile['product_service']}{style_info}

## 第三步：语义改写策略
{strategy_desc}

**关键要求**：
1. **不要逐字替换**，而是理解原标题的吸引力逻辑后重新创作
2. **保留爆款结构**（如果有数字保留数字位置，有对比保留对比结构）
3. **完全IP化**：用IP的专业领域、经验、观点来重构内容
4. **语言风格化**：使用IP习惯的表达方式，像TA本人说的话
5. **保持自然流畅**：改写后的标题应该像原创，不生硬

## 示例
原标题："90后宝妈靠副业月入过万，分享3个真实方法"
- 爆款逻辑：身份标签（宝妈）+ 金钱结果（月入过万）+ 干货承诺（3个方法）
- 情绪：希望（普通人也能赚钱）

IP人设：UI设计师，擅长AI工具，受众是设计师
改写后：" UI设计师靠AI接私单月入3万，分享我的3个获客渠道"
（保留：身份+收入+干货结构，但完全换成设计师领域的内容）

## 当前改写任务
原标题：{original_title}
- Hook: {original_hook}
- Body: {original_body}
- 内容类型: {content_type}
- 标签: {', '.join(tags)}

请先用一句话分析原标题的爆款逻辑，然后给出改写版本。

## 输出格式（JSON）
{{
    "analysis": "原标题爆款逻辑分析（一句话）",
    "title": "改写后的完整标题",
    "hook": "改写后的hook部分",
    "body": "改写后的body部分",
    "strategy_note": "改写策略说明"
}}

请直接输出JSON，不要包含其他内容。"""

        return prompt
    
    def _parse_ai_response(self, response: str) -> Dict[str, str]:
        """解析AI响应 - 支持语义分析版本"""
        try:
            # 尝试直接解析JSON
            result = json.loads(response.strip())
            return {
                "analysis": result.get("analysis", ""),
                "title": result.get("title", ""),
                "hook": result.get("hook", ""),
                "body": result.get("body", ""),
                "strategy_note": result.get("strategy_note", "")
            }
        except json.JSONDecodeError:
            # 如果解析失败，尝试提取JSON部分
            import re
            # 匹配更复杂的JSON（包含嵌套）
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return {
                        "analysis": result.get("analysis", ""),
                        "title": result.get("title", ""),
                        "hook": result.get("hook", ""),
                        "body": result.get("body", ""),
                        "strategy_note": result.get("strategy_note", "")
                    }
                except:
                    pass
            
            # 降级：尝试提取引号中的内容作为标题
            title_match = re.search(r'"title"[:\s]*"([^"]+)"', response)
            hook_match = re.search(r'"hook"[:\s]*"([^"]+)"', response)
            body_match = re.search(r'"body"[:\s]*"([^"]*)"', response)
            
            if title_match:
                return {
                    "analysis": "",
                    "title": title_match.group(1),
                    "hook": hook_match.group(1) if hook_match else "",
                    "body": body_match.group(1) if body_match else "",
                    "strategy_note": "从非JSON格式中提取"
                }
            
            # 最终降级：返回原始响应
            return {
                "analysis": "",
                "title": response.strip()[:50],
                "hook": response.strip()[:20],
                "body": "",
                "strategy_note": "解析失败，使用原始响应"
            }
    
    def _rule_based_rewrite(
        self,
        ip_profile: Dict[str, Any],
        original_title: str,
        original_hook: str,
        original_body: str,
        content_type: str
    ) -> RewriteResult:
        """
        基于规则的改写（AI失败时的降级方案）
        更智能的替换策略
        """
        nickname = ip_profile['nickname']
        expertise = ip_profile['expertise']
        content_direction = ip_profile.get('content_direction', '')
        
        rewritten_hook = original_hook
        rewritten_body = original_body
        
        # 1. 识别并替换身份标签
        identity_patterns = [
            ("宝妈", ["设计师", "创作者"]),
            ("妈妈", ["设计师", "创作者"]),
            ("打工人", ["设计师", "自由职业者"]),
            ("上班族", ["设计师", "自由职业者"]),
            ("90后", [""]),  # 保留年龄，后面加身份
            ("00后", [""]),
        ]
        
        for pattern, replacements in identity_patterns:
            if pattern in rewritten_hook:
                # 如果有专业领域，用领域+身份替换
                if expertise:
                    # 提取领域中的第一个关键词
                    field = expertise.split("、")[0].split(",")[0].strip()
                    if pattern in ["90后", "00后"]:
                        # 在年龄后添加身份
                        rewritten_hook = rewritten_hook.replace(pattern, f"{pattern}{field}")
                    else:
                        # 直接用领域身份替换
                        rewritten_hook = rewritten_hook.replace(pattern, field)
                break
        
        # 2. 如果hook中没有IP相关信息，添加昵称
        if nickname not in rewritten_hook and not any(kw in rewritten_hook for kw in ["我", "我的"]):
            # 在开头添加"我是"+昵称
            if rewritten_hook.startswith(("90后", "00后", "32岁", "28岁")):
                # 在年龄后添加身份说明
                pass  # 已经在上面处理
            else:
                # 在前面添加昵称
                rewritten_hook = f"我是{nickname}，{rewritten_hook}"
        
        # 3. 改写body，加入专业视角
        if rewritten_body:
            # 检查是否已经是分享/教程类
            if any(kw in rewritten_body for kw in ["分享", "教你", "方法", "技巧"]):
                # 添加专业领域前缀
                if expertise and "设计师" not in rewritten_body:
                    rewritten_body = f"{nickname}的{expertise}{rewritten_body}"
            else:
                # 添加视角说明
                if content_direction:
                    rewritten_body = f"{content_direction}：{rewritten_body}"
        else:
            # 如果body为空，生成一个默认的
            if content_direction:
                rewritten_body = f"分享我的{content_direction}经验"
            elif expertise:
                rewritten_body = f"{nickname}的{expertise}心得"
        
        # 4. 组合标题
        rewritten_title = f"{rewritten_hook}，{rewritten_body}" if rewritten_body else rewritten_hook
        
        return RewriteResult(
            original_title=original_title,
            original_hook=original_hook,
            original_body=original_body,
            rewritten_title=rewritten_title,
            rewritten_hook=rewritten_hook,
            rewritten_body=rewritten_body,
            strategy="rule_based_fallback",
            ip_id=ip_profile.get('ip_id', ''),
            ip_name=ip_profile['name'],
            content_type=content_type,
            success=True
        )


# 便捷函数
_rewrite_service: Optional[TitleRewriteService] = None


def get_rewrite_service() -> TitleRewriteService:
    """获取全局改写服务实例"""
    global _rewrite_service
    if _rewrite_service is None:
        _rewrite_service = TitleRewriteService()
    return _rewrite_service


async def rewrite_title(
    ip_id: str,
    original_title: str,
    original_hook: str,
    original_body: str,
    tags: List[str],
    content_type: str,
    strategy: str = "structure_keep"
) -> Dict[str, Any]:
    """
    便捷函数：改写标题
    """
    service = get_rewrite_service()
    result = await service.rewrite(
        ip_id=ip_id,
        original_title=original_title,
        original_hook=original_hook,
        original_body=original_body,
        tags=tags,
        content_type=content_type,
        strategy=strategy
    )
    return result.to_dict()
