"""
Creator API Router
对接前端 /api/creator/* 路由
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
import asyncio

from app.db import get_db
from app.db.models import IP
from app.services.content_scenario import (
    ContentGenerator,
    ScenarioOneRequest,
    ScenarioTwoRequest,
    ScenarioThreeRequest,
    FourDimWeights,
)

router = APIRouter(prefix="/creator", tags=["creator"])


def get_ip_profile(db, ip_id: str):
    """获取IP画像"""
    ip = db.query(IP).filter(IP.id == ip_id).first()
    if not ip:
        return None
    return {
        "name": ip.name,
        "style": ip.style or "",
        "target_audience": ip.target_audience or "",
        "content_preference": ip.content_preference or "",
    }


# === 场景一：推荐选题生成 ===
class TopicGenerateRequest(BaseModel):
    topicId: str
    style: str  # angry/calm/humor
    ipId: Optional[str] = "1"


@router.post("/generate/topic")
async def generate_from_topic(req: TopicGenerateRequest, db=Depends(get_db)):
    """场景一：从选题生成内容"""
    try:
        # 获取IP画像
        ip_profile = get_ip_profile(db, req.ipId)
        
        # 构建请求 - 使用 scenario_one
        request = ScenarioOneRequest(
            ip_id=req.ipId,
            platform="douyin",
            ip_profile=ip_profile,
            weights=FourDimWeights(
                relevance=0.3,
                hotness=0.3,
                competition=0.2,
                conversion=0.2,
            ),
            count=1,
        )
        
        # 调用真实生成
        results = await ContentGenerator.scenario_one(request)
        
        if results:
            result = results[0]
            return {
                "id": f"gen_{req.topicId}",
                "status": "completed",
                "progress": 100,
                "estimatedTime": 0,
                "content": result.content,
                "score": result.score,
            }
        else:
            return {
                "id": f"gen_{req.topicId}",
                "status": "failed",
                "progress": 0,
                "error": "生成失败"
            }
    except Exception as e:
        return {
            "id": f"gen_{req.topicId}",
            "status": "failed",
            "error": str(e)
        }


# === 场景二：仿写爆款 ===
class RemixGenerateRequest(BaseModel):
    url: str
    style: str
    ipId: Optional[str] = "1"


@router.post("/generate/remix")
async def generate_from_remix(req: RemixGenerateRequest, db=Depends(get_db)):
    """场景二：仿写爆款"""
    try:
        ip_profile = get_ip_profile(db, req.ipId)
        
        request = ScenarioTwoRequest(
            ip_id=req.ipId,
            competitor_url=req.url,
            ip_profile=ip_profile,
            rewrite_level=0.7,
        )
        
        result = await ContentGenerator.scenario_two(request)
        
        return {
            "id": "gen_remix_001",
            "status": "completed",
            "progress": 100,
            "estimatedTime": 0,
            "content": result.content,
            "score": result.score,
        }
    except Exception as e:
        return {
            "id": "gen_remix_001",
            "status": "failed",
            "error": str(e)
        }


# === 场景三：爆款原创 ===
class ViralGenerateRequest(BaseModel):
    input: str
    inputMode: str  # text/voice/file
    scriptTemplate: str
    viralElements: List[str]
    targetDuration: int
    style: str
    ipId: Optional[str] = "1"


@router.post("/generate/viral")
async def generate_viral_original(req: ViralGenerateRequest, db=Depends(get_db)):
    """场景三：爆款原创"""
    try:
        ip_profile = get_ip_profile(db, req.ipId)
        
        request = ScenarioThreeRequest(
            ip_id=req.ipId,
            topic=req.input,
            style_profile=ip_profile,
            key_points=req.viralElements,
            length=req.targetDuration,
        )
        
        result = await ContentGenerator.scenario_three(request)
        
        return {
            "id": "gen_viral_001",
            "status": "completed",
            "progress": 100,
            "estimatedTime": 0,
            "content": result.content,
            "score": result.score,
        }
    except Exception as e:
        return {
            "id": "gen_viral_001",
            "status": "failed",
            "error": str(e)
        }


# === 获取生成结果 ===
@router.get("/generate/{id}/result")
async def get_generate_result(id: str):
    """获取生成结果"""
    # TODO: 从数据库或缓存获取真实结果
    return {
        "id": id,
        "title": "测试内容",
        "hook": "钩子示例...",
        "story": "故事示例...",
        "opinion": "观点示例...",
        "cta": "行动指令示例...",
        "style": "angry",
        "compliance": {
            "originalityScore": 82,
            "sensitiveWords": [],
            "platformChecks": {"douyin": "passed", "xiaohongshu": "passed"}
        }
    }


# === 获取生成进度 ===
@router.get("/generate/{id}/progress")
async def get_generate_progress(id: str):
    """获取生成进度"""
    return {
        "id": id,
        "status": "completed",
        "progress": 100,
        "estimatedTime": 0
    }


# === 获取推荐选题 ===
@router.get("/topics/recommended")
async def get_recommended_topics():
    """获取推荐选题"""
    return {
        "topics": [
            {"id": "1", "title": "现金流断裂如何自救", "score": 4.8},
            {"id": "2", "title": "为什么90%的IP都在第一步做错了？", "score": 4.7},
            {"id": "3", "title": "月入3万的私域运营", "score": 4.7}
        ]
    }


# === Agent状态 ===
@router.get("/agent-status")
async def get_agent_status():
    """获取Agent配置状态"""
    return {
        "strategy": {"status": "ready", "config": ["四维权重", "竞品监控"]},
        "memory": {"status": "ready", "config": ["标签体系", "检索策略"]},
        "remix": {"status": "ready", "config": ["解构规则"]},
        "generation": {"status": "ready", "config": ["风格训练", "口头禅"]},
        "compliance": {"status": "ready", "config": ["敏感词库"]}
    }
