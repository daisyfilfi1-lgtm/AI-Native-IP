"""
多模态处理路由
"""
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.memory_config_service import get_ip as get_ip_model
from app.services.multimodal_service import (
    MultimodalConfig,
    analyze_image,
    analyze_video_with_llm,
    batch_analyze_images,
    create_multimodal_asset,
    extract_audio_topics,
    generate_video_summary,
)

router = APIRouter()


class VideoAnalyzeRequest(BaseModel):
    video_url: str
    prompt: Optional[str] = None


class ImageAnalyzeRequest(BaseModel):
    image_url: str
    prompt: Optional[str] = None


class BatchImageRequest(BaseModel):
    image_urls: List[str]
    prompt: Optional[str] = None


class AudioTopicRequest(BaseModel):
    audio_text: str
    max_topics: Optional[int] = 5


class MultimodalAssetRequest(BaseModel):
    ip_id: str
    source_type: str = Field(..., description="video|image|audio")
    source_url: str
    content: str = ""  # 音频时为转写文本
    title: Optional[str] = None


# ==================== 视频分析 ====================

@router.post("/multimodal/video/analyze")
def analyze_video(
    payload: VideoAnalyzeRequest,
):
    """
    分析视频内容
    
    自动提取关键帧并使用视觉LLM分析
    需要配置支持视觉的模型（如GPT-4V）
    """
    if not payload.video_url:
        raise HTTPException(status_code=400, detail="请提供视频URL")
    
    result = analyze_video_with_llm(payload.video_url, payload.prompt)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/multimodal/video/summary")
def video_summary(
    payload: VideoAnalyzeRequest,
):
    """生成视频内容摘要"""
    if not payload.video_url:
        raise HTTPException(status_code=400, detail="请提供视频URL")
    
    result = generate_video_summary(payload.video_url)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


# ==================== 图像分析 ====================

@router.post("/multimodal/image/analyze")
def analyze_image_endpoint(
    payload: ImageAnalyzeRequest,
):
    """
    分析图片内容
    
    支持：
    - 远程图片URL
    - base64图片（data:image/xxx;base64,xxx）
    """
    if not payload.image_url:
        raise HTTPException(status_code=400, detail="请提供图片URL")
    
    result = analyze_image(payload.image_url, payload.prompt)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/multimodal/image/batch")
def batch_analyze_images_endpoint(
    payload: BatchImageRequest,
):
    """批量分析多张图片"""
    if not payload.image_urls:
        raise HTTPException(status_code=400, detail="请提供图片列表")
    
    if len(payload.image_urls) > 20:
        raise HTTPException(status_code=400, detail="最多支持20张图片")
    
    result = batch_analyze_images(payload.image_urls, payload.prompt)
    return result


# ==================== 音频分析 ====================

@router.post("/multimodal/audio/topics")
def extract_audio_topics_endpoint(
    payload: AudioTopicRequest,
):
    """
    从音频转写文本中提取主题和关键信息
    
    返回：
    - 主题标签
    - 核心观点
    - 情感倾向
    - 适合的内容形式
    """
    if not payload.audio_text:
        raise HTTPException(status_code=400, detail="请提供音频转写文本")
    
    result = extract_audio_topics(payload.audio_text, payload.max_topics or 5)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


# ==================== 多模态素材创建 ====================

@router.post("/multimodal/asset")
def create_multimodal_asset_endpoint(
    payload: MultimodalAssetRequest,
    db: Session = Depends(get_db),
):
    """
    创建多模态素材
    
    自动进行内容理解、标签提取、向量存储
    支持video/image/audio三种类型
    """
    if not get_ip_model(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    
    if payload.source_type not in ("video", "image", "audio"):
        raise HTTPException(status_code=400, detail="source_type必须是video/image/audio")
    
    metadata = {
        "title": payload.title or f"多模态素材_{payload.source_type}",
    }
    
    result = create_multimodal_asset(
        db=db,
        ip_id=payload.ip_id,
        source_type=payload.source_type,
        source_url=payload.source_url,
        content=payload.content,
        metadata=metadata,
    )
    
    return result


# ==================== 配置 ====================

@router.get("/multimodal/config")
def get_multimodal_config():
    """获取多模态配置"""
    return {
        "video_keyframe_interval": MultimodalConfig.VIDEO_KEYFRAME_INTERVAL,
        "video_max_frames": MultimodalConfig.VIDEO_MAX_FRAMES,
        "vision_model": MultimodalConfig.VISION_MODEL,
    }
