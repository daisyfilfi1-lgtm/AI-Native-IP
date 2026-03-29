"""
环节4：改写标题 + IP素材 → 内容生成

复用content_scenario.py中已打磨的"爆款原创"生成逻辑。
三个场景统一走ScenarioThreeGenerator（自定义原创）的生成流程。
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.db.models import IP
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@dataclass
class ContentGenerationResult:
    """内容生成结果"""
    # 输入信息
    ip_id: str
    ip_name: str
    title: str  # 改写后的标题
    hook: str
    body: str
    
    # 生成内容
    content: str  # 完整口播稿
    score: float = 0.0
    
    # 元数据
    word_count: int = 0
    estimated_duration: int = 0  # 预估时长（秒）
    
    # 状态
    success: bool = False
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "error": self.error,
            "ip_id": self.ip_id,
            "ip_name": self.ip_name,
            "title": self.title,
            "hook": self.hook,
            "body": self.body,
            "content": self.content,
            "score": self.score,
            "word_count": self.word_count,
            "estimated_duration": self.estimated_duration
        }


class ContentGenerationService:
    """
    内容生成服务 - 复用content_scenario.py的打磨逻辑
    
    核心：直接调用ScenarioThreeGenerator（自定义原创）的生成流程
    """
    
    async def generate(
        self,
        ip_id: str,
        title: str,
        hook: str,
        body: str,
        content_type: str = "life",
        target_duration: int = 60,
        **kwargs
    ) -> ContentGenerationResult:
        """
        生成内容 - 复用已打磨的爆款原创逻辑
        
        Args:
            ip_id: IP ID
            title: 完整标题
            hook: hook部分
            body: body部分  
            content_type: 内容类型（决定长度）
            target_duration: 目标时长（秒）
        """
        db = SessionLocal()
        try:
            # 获取IP信息
            ip = db.query(IP).filter(IP.ip_id == ip_id).first()
            if not ip:
                return ContentGenerationResult(
                    ip_id=ip_id,
                    ip_name="",
                    title=title,
                    hook=hook,
                    body=body,
                    content="",
                    success=False,
                    error=f"IP not found: {ip_id}"
                )
            
            # 构建IP画像
            ip_profile = self._build_ip_profile(ip)
            
            # 构建风格画像
            style_profile = self._build_style_profile(ip)
            
            # 长度映射
            length_map = {
                "money": "medium",
                "emotion": "medium", 
                "skill": "long",
                "life": "short"
            }
            length = length_map.get(content_type, "medium")
            
            # 关键要点（从hook和body提取）
            key_points = [
                hook,
                body,
                f"内容类型: {content_type}"
            ]
            
            # 调用已打磨的ScenarioThreeGenerator
            from app.services.content_scenario import ScenarioThreeGenerator
            
            generator = ScenarioThreeGenerator(
                ip_profile=ip_profile,
                style_profile=style_profile
            )
            
            result = await generator.generate(
                topic=title,
                key_points=key_points,
                length=length
            )
            
            # 计算字数和时长
            content = result.content or ""
            word_count = len(content)
            estimated_duration = word_count // 4  # 约每秒4个字
            
            return ContentGenerationResult(
                ip_id=ip_id,
                ip_name=ip.name,
                title=title,
                hook=hook,
                body=body,
                content=content,
                score=result.score,
                word_count=word_count,
                estimated_duration=estimated_duration,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return ContentGenerationResult(
                ip_id=ip_id,
                ip_name=ip.name if 'ip' in dir() else "",
                title=title,
                hook=hook,
                body=body,
                content="",
                success=False,
                error=str(e)
            )
        finally:
            db.close()
    
    def _build_ip_profile(self, ip: IP) -> Dict[str, Any]:
        """构建IP画像"""
        return {
            "ip_id": ip.ip_id,
            "name": ip.name,
            "nickname": ip.nickname or ip.name,
            "bio": ip.bio or "",
            "expertise": ip.expertise or "",
            "passion": ip.passion or "",
            "content_direction": ip.content_direction or "",
            "target_audience": ip.target_audience or "",
            "unique_value_prop": ip.unique_value_prop or "",
            "style_profile": ip.style_profile or {}
        }
    
    def _build_style_profile(self, ip: IP) -> Dict[str, Any]:
        """构建风格画像"""
        style = ip.style_profile or {}
        return {
            "tone": style.get("tone", ["亲切", "专业"]),
            "vocabulary": style.get("vocabulary", []),
            "sentence_patterns": style.get("sentence_patterns", []),
            "catchphrases": style.get("catchphrases", []),
            "imperfection_score": style.get("imperfection_score", 0.6),
            "burstiness_score": style.get("burstiness_score", 0.5)
        }


# 便捷函数
_generation_service: Optional[ContentGenerationService] = None


def get_generation_service() -> ContentGenerationService:
    """获取全局内容生成服务实例"""
    global _generation_service
    if _generation_service is None:
        _generation_service = ContentGenerationService()
    return _generation_service


async def generate_content(
    ip_id: str,
    title: str,
    hook: str,
    body: str,
    content_type: str = "life",
    target_duration: int = 60,
    **kwargs
) -> Dict[str, Any]:
    """
    便捷函数：生成内容
    
    复用content_scenario.py中已打磨的ScenarioThreeGenerator
    """
    service = get_generation_service()
    result = await service.generate(
        ip_id=ip_id,
        title=title,
        hook=hook,
        body=body,
        content_type=content_type,
        target_duration=target_duration,
        **kwargs
    )
    return result.to_dict()
