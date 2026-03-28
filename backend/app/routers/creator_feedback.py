"""
Creator Feedback Router - 用户重写反馈系统
用于自进化分析，收集用户重写时的原因
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import ContentDraft, RewriteFeedback
from app.db.session import get_db

router = APIRouter(prefix="/creator", tags=["creator"])


# === 重写反馈 ===
class RewriteFeedbackRequest(BaseModel):
    draft_id: str
    ip_id: str
    rewrite_reason: str  # tag_story/tag_structure/tag_ip_position/tag_ai_flavor/tag_general
    user_comment: Optional[str] = None


@router.post("/feedback/rewrite")
async def submit_rewrite_feedback(
    req: RewriteFeedbackRequest,
    db: Session = Depends(get_db),
):
    """
    用户重写反馈（用于自进化分析）
    只有在用户点击重写时才会触发，数据质量高
    """
    # 验证 draft 存在
    draft = db.query(ContentDraft).filter(ContentDraft.draft_id == req.draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="内容不存在")
    
    # 检查重复反馈
    existing = db.query(RewriteFeedback).filter(
        RewriteFeedback.draft_id == req.draft_id
    ).first()
    if existing:
        # 已有过反馈，更新
        existing.rewrite_reason = req.rewrite_reason
        existing.user_comment = req.user_comment
    else:
        # 新建反馈
        feedback = RewriteFeedback(
            draft_id=req.draft_id,
            ip_id=req.ip_id,
            rewrite_reason=req.rewrite_reason,
            user_comment=req.user_comment,
        )
        db.add(feedback)
    
    db.commit()
    
    # 统计返回（给前端展示）
    stats = db.query(RewriteFeedback).filter(
        RewriteFeedback.ip_id == req.ip_id
    ).all()
    
    reason_counts = {}
    for f in stats:
        reason_counts[f.rewrite_reason] = reason_counts.get(f.rewrite_reason, 0) + 1
    
    return {
        "ok": True,
        "message": "反馈已记录，感谢您的意见",
        "stats": reason_counts
    }


@router.get("/feedback/stats")
async def get_feedback_stats(
    ipId: str = Query(..., description="IP画像ID"),
    db: Session = Depends(get_db),
):
    """
    获取反馈统计数据（用于自进化分析）
    """
    feedbacks = db.query(RewriteFeedback).filter(
        RewriteFeedback.ip_id == ipId
    ).order_by(RewriteFeedback.created_at.desc()).limit(100).all()
    
    if not feedbacks:
        return {
            "ip_id": ipId,
            "total": 0,
            "reason_counts": {},
            "recent": []
        }
    
    reason_counts = {}
    for f in feedbacks:
        reason_counts[f.rewrite_reason] = reason_counts.get(f.rewrite_reason, 0) + 1
    
    return {
        "ip_id": ipId,
        "total": len(feedbacks),
        "reason_counts": reason_counts,
        "recent": [
            {
                "reason": f.rewrite_reason,
                "comment": f.user_comment,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in feedbacks[:10]
        ]
    }
