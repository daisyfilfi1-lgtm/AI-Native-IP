"""
多模态服务 - 视频/音频/图像理解
支持视频关键帧提取、音频分析、图像理解
"""
import os
import re
import uuid
from typing import Any, List, Optional
from datetime import datetime

import requests
from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.ai_client import chat, embed, get_ai_config


class MultimodalConfig:
    """多模态配置"""
    
    # 视频处理
    VIDEO_KEYFRAME_INTERVAL = 30  # 每30秒提取一帧
    VIDEO_MAX_FRAMES = 10         # 最多提取帧数
    
    # 图像处理
    IMAGE_ANALYSIS_ENABLED = True
    
    # 音频处理
    AUDIO_SUMMARY_ENABLED = True
    
    # LLM模型（用于多模态理解）
    VISION_MODEL = "gpt-4o"       # 支持视觉的模型


def extract_video_keyframes(video_url: str) -> List[dict]:
    """
    提取视频关键帧
    使用FFmpeg提取关键帧（需要本地部署ffmpeg）
    
    返回关键帧图片的base64列表
    """
    import base64
    import subprocess
    import tempfile
    
    keyframes = []
    
    try:
        # 获取视频时长
        cmd = [
            "ffprobe", 
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        duration = float(result.stdout.strip() or 0)
        
        if duration <= 0:
            return [{"error": "无法获取视频时长"}]
        
        # 计算提取帧的时间点
        interval = min(
            MultimodalConfig.VIDEO_KEYFRAME_INTERVAL,
            duration / MultimodalConfig.VIDEO_MAX_FRAMES
        )
        
        timestamps = []
        t = 0
        while t < duration and len(timestamps) < MultimodalConfig.VIDEO_MAX_FRAMES:
            timestamps.append(t)
            t += interval
        
        # 提取关键帧
        for ts in timestamps:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(ts),
                    "-i", video_url,
                    "-vframes", "1",
                    "-q:v", "2",
                    tmp.name
                ]
                try:
                    subprocess.run(cmd, capture_output=True, timeout=10)
                    
                    # 读取图片并转为base64
                    with open(tmp.name, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                        keyframes.append({
                            "timestamp": ts,
                            "image_base64": img_data,
                        })
                except Exception as e:
                    keyframes.append({"timestamp": ts, "error": str(e)})
                finally:
                    os.unlink(tmp.name)
        
        return keyframes
        
    except Exception as e:
        return [{"error": str(e)}]


def analyze_video_with_llm(video_url: str, prompt: str = None) -> dict:
    """
    使用支持视觉的LLM分析视频（通过提取关键帧）
    
    注意：需要配置支持视觉的API（如OpenAI GPT-4V）
    """
    if not prompt:
        prompt = """分析这个视频：
1. 视频的主要内容主题是什么？
2. 视频中出现的核心人物/物品/场景？
3. 视频传达的情感/价值观？
4. 适合什么类型的内容创作？
"""
    
    cfg = get_ai_config()
    vision_model = os.environ.get("VISION_MODEL", MultimodalConfig.VISION_MODEL)
    
    # 提取关键帧
    keyframes = extract_video_keyframes(video_url)
    
    if not keyframes or keyframes[0].get("error"):
        return {"error": keyframes[0].get("error") if keyframes else "无法提取关键帧"}
    
    # 取前3帧进行分析
    frames_to_analyze = keyframes[:3]
    
    # 构建多模态消息
    content = [{"type": "text", "text": prompt}]
    
    for frame in frames_to_analyze:
        if "image_base64" in frame:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame['image_base64']}"
                }
            })
    
    try:
        response = chat(
            model=vision_model,
            messages=[
                {"role": "user", "content": content}
            ],
            temperature=0.3,
        )
        
        return {
            "analysis": response,
            "keyframes_count": len(keyframes),
            "frames_analyzed": len(frames_to_analyze),
        }
        
    except Exception as e:
        return {"error": str(e)}


def generate_video_summary(video_url: str) -> dict:
    """生成视频内容的文字摘要"""
    prompt = """请详细描述这个视频的内容，包括：
1. 视频主题/话题
2. 关键人物和他们的言论
3. 重要场景和背景
4. 核心观点或故事情节
5. 适合作为什么类型的创作素材？

请用详细、结构化的方式描述。"""
    
    return analyze_video_with_llm(video_url, prompt)


def analyze_image(image_url: str, prompt: str = None) -> dict:
    """
    分析图片内容
    
    支持：
    - URL远程图片
    - base64本地图片
    """
    if not prompt:
        prompt = """分析这张图片：
1. 图片主要内容是什么？
2. 视觉风格/色调
3. 适合配合什么文字内容使用？
4. 可以提取哪些标签/关键词？
"""
    
    cfg = get_ai_config()
    vision_model = os.environ.get("VISION_MODEL", MultimodalConfig.VISION_MODEL)
    
    # 判断图片来源
    if image_url.startswith("data:"):
        # base64
        image_content = {"url": image_url}
    elif image_url.startswith("http"):
        # URL
        image_content = {"url": image_url}
    else:
        return {"error": "不支持的图片格式"}
    
    try:
        response = chat(
            model=vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": image_content}
                    ]
                }
            ],
            temperature=0.3,
        )
        
        return {"analysis": response}
        
    except Exception as e:
        return {"error": str(e)}


def extract_audio_topics(audio_text: str, max_topics: int = 5) -> dict:
    """从音频转写文本中提取主题和关键信息"""
    
    prompt = f"""从以下音频转写文本中提取：

1. 主题标签（{max_topics}个）
2. 核心观点（3个）
3. 情感倾向（正面/中性/负面）
4. 适合的内容形式（故事/观点/干货/情感等）

转写文本：
{audio_text[:3000]}

请用JSON格式返回：
{{
  "topics": ["标签1", "标签2"],
  "core_points": ["观点1", "观点2"],
  "sentiment": "positive/neutral/negative",
  "content_types": ["story", "opinion"]
}}
"""
    
    try:
        response = chat(
            model=get_ai_config().get("llm_model", "deepseek-chat"),
            messages=[
                {"role": "system", "content": "你是一个内容分析专家，擅长从文本中提取关键信息。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        # 尝试解析JSON
        import json
        try:
            # 提取JSON部分
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            result = json.loads(response.strip())
            return result
        except:
            return {"raw_analysis": response}
            
    except Exception as e:
        return {"error": str(e)}


def create_multimodal_asset(
    db: Session,
    ip_id: str,
    source_type: str,
    source_url: str,
    content: str,
    metadata: dict,
) -> dict:
    """
    创建多模态素材
    自动进行内容理解并生成标签
    """
    asset_id = f"mm_{uuid.uuid4().hex[:12]}"
    
    # 基于内容类型进行理解
    analysis = {}
    
    if source_type == "video":
        if "http" in source_url:
            analysis = generate_video_summary(source_url)
        else:
            analysis = {"error": "视频理解需要URL"}
    
    elif source_type == "image":
        if "http" in source_url or source_url.startswith("data:"):
            analysis = analyze_image(source_url)
        else:
            analysis = {"error": "图片理解需要URL或base64"}
    
    elif source_type == "audio":
        if content:  # 有转写文本
            analysis = extract_audio_topics(content)
        else:
            analysis = {"error": "需要提供转写文本"}
    
    # 合并metadata
    full_metadata = {
        **metadata,
        "source_type": source_type,
        "multimodal_analysis": analysis,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # 生成embedding
    embedding_text = content
    if analysis.get("analysis"):
        embedding_text += "\n\n" + str(analysis["analysis"])
    
    vectors = embed([embedding_text])
    vector = vectors[0] if vectors else None
    
    # 写入数据库
    asset = IPAsset(
        asset_id=asset_id,
        ip_id=ip_id,
        asset_type=source_type,  # video/image/audio
        title=metadata.get("title", f"多模态素材_{source_type}"),
        content=content,
        content_vector_ref=None,
        asset_meta=full_metadata,
        relations=[],
        status="active",
    )
    
    db.add(asset)
    db.commit()
    
    return {
        "asset_id": asset_id,
        "analysis": analysis,
        "vector_created": vector is not None,
    }


def batch_analyze_images(image_urls: List[str], prompt: str = None) -> dict:
    """批量分析多张图片"""
    results = []
    
    for url in image_urls:
        result = analyze_image(url, prompt)
        results.append({
            "url": url,
            "result": result,
        })
    
    # 汇总分析
    all_topics = []
    all_styles = []
    
    for r in results:
        if "analysis" in r["result"]:
            # 简化：假设analysis包含主题和风格
            all_topics.append(r["result"]["analysis"][:100])
    
    return {
        "total": len(image_urls),
        "results": results,
        "summary": "\n".join(all_topics[:3]),
    }
