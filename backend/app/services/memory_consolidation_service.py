"""
记忆Consolidation服务 - 记忆分级、知识提炼、归档
实现长期记忆质量优化
"""
import os
from datetime import datetime, timedelta
from typing import Any, List, Optional
from collections import defaultdict

from sqlalchemy.orm import Session

from app.db.models import IPAsset
from app.services.ai_client import chat, get_ai_config


class MemoryLevel:
    """记忆分级"""
    CORE = "core"          # 核心记忆（重要、常用）
    ACTIVE = "active"      # 活跃记忆
    ARCHIVE = "archive"    # 归档记忆（冷门）
    
    # 阈值配置
    CORE_USAGE_THRESHOLD = 10      # 使用次数达到此值晋升为核心
    ARCHIVE_USAGE_THRESHOLD = 0    # 使用次数低于此值降级为归档
    ARCHIVE_DAYS = 90              # 多少天未使用归档


class MemoryConsolidation:
    """记忆Consolidation引擎"""
    
    def __init__(self, db: Session, ip_id: str):
        self.db = db
        self.ip_id = ip_id
    
    def get_memory_stats(self) -> dict:
        """获取记忆统计"""
        assets = self.db.query(IPAsset).filter(
            IPAsset.ip_id == self.ip_id,
            IPAsset.status == "active",
        ).all()
        
        stats = {
            "total": len(assets),
            "by_level": {
                MemoryLevel.CORE: 0,
                MemoryLevel.ACTIVE: 0,
                MemoryLevel.ARCHIVE: 0,
            },
            "usage_counts": [],
            "avg_usage": 0,
        }
        
        total_usage = 0
        for asset in assets:
            meta = asset.asset_meta or {}
            level = meta.get("memory_level", MemoryLevel.ACTIVE)
            usage_count = meta.get("usage_count", 0)
            
            stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
            stats["usage_counts"].append(usage_count)
            total_usage += usage_count
        
        if assets:
            stats["avg_usage"] = total_usage / len(assets)
        
        return stats
    
    def record_usage(self, asset_id: str) -> bool:
        """记录一次记忆使用"""
        asset = self.db.query(IPAsset).filter(
            IPAsset.asset_id == asset_id,
            IPAsset.ip_id == self.ip_id,
        ).first()
        
        if not asset:
            return False
        
        meta = asset.asset_meta or {}
        
        # 增加使用计数
        current_count = meta.get("usage_count", 0)
        meta["usage_count"] = current_count + 1
        meta["last_used_at"] = datetime.utcnow().isoformat()
        
        # 检查是否晋升为核心记忆
        if current_count + 1 >= MemoryLevel.CORE_USAGE_THRESHOLD:
            meta["memory_level"] = MemoryLevel.CORE
        
        asset.asset_meta = meta
        self.db.commit()
        
        return True
    
    def consolidate(self) -> dict:
        """
        执行记忆Consolidation
        1. 统计使用情况
        2. 调整记忆级别
        3. 提炼核心知识
        4. 归档冷门内容
        """
        assets = self.db.query(IPAsset).filter(
            IPAsset.ip_id == self.ip_id,
            IPAsset.status == "active",
        ).all()
        
        now = datetime.utcnow()
        promoted = 0
        demoted = 0
        archived = 0
        
        core_contents = []  # 收集核心记忆用于提炼
        
        for asset in assets:
            meta = asset.asset_meta or {}
            usage_count = meta.get("usage_count", 0)
            last_used = meta.get("last_used_at")
            current_level = meta.get("memory_level", MemoryLevel.ACTIVE)
            
            # 计算天数
            days_since_use = 0
            if last_used:
                try:
                    last_used_dt = datetime.fromisoformat(last_used)
                    days_since_use = (now - last_used_dt).days
                except:
                    pass
            
            new_level = current_level
            
            # 归档判断：长期未使用
            if days_since_use > MemoryLevel.ARCHIVE_DAYS and current_level != MemoryLevel.ARCHIVE:
                new_level = MemoryLevel.ARCHIVE
                demoted += 1
                archived += 1
            
            # 晋升判断：高使用频率
            elif usage_count >= MemoryLevel.CORE_USAGE_THRESHOLD and current_level != MemoryLevel.CORE:
                new_level = MemoryLevel.CORE
                promoted += 1
            
            # 收集核心记忆内容用于提炼
            if new_level == MemoryLevel.CORE:
                core_contents.append({
                    "asset_id": asset.asset_id,
                    "title": asset.title,
                    "content": asset.content,
                })
            
            # 更新记忆级别
            if new_level != current_level:
                meta["memory_level"] = new_level
                meta["level_changed_at"] = now.isoformat()
                asset.asset_meta = meta
        
        self.db.commit()
        
        # 提炼核心知识
        summary = None
        if core_contents:
            try:
                summary = self._generate_core_summary(core_contents)
            except Exception as e:
                print(f"Summary generation failed: {e}")
        
        return {
            "total_assets": len(assets),
            "promoted": promoted,
            "demoted": demoted,
            "archived": archived,
            "core_summary": summary,
        }
    
    def _generate_core_summary(self, core_contents: List[dict]) -> str:
        """使用LLM从核心记忆提炼摘要"""
        client = get_client()
        
        # 取最核心的5条
        content_texts = [f"- {c['title']}: {c['content'][:300]}..." for c in core_contents[:5]]
        content_str = "\n".join(content_texts)
        
        prompt = f"""基于以下IP的核心记忆内容，提炼出该IP的核心价值观、风格特点、专业领域。

核心记忆内容：
{content_str}

请提炼成3-5句话的精炼摘要，格式如下：
【核心身份】xxx
【内容风格】xxx
【专业领域】xxx
【常用话题】xxx
"""
        
        cfg = get_ai_config()
        model = cfg.get("llm_model", "deepseek-chat")
        
        response = chat(
            model=model,
            messages=[
                {"role": "system", "content": "你是内容策略专家，擅长提炼IP核心特征。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        return response.choices[0].message.content
    
    def get_core_memory(self, limit: int = 10) -> List[dict]:
        """获取核心记忆"""
        assets = self.db.query(IPAsset).filter(
            IPAsset.ip_id == self.ip_id,
            IPAsset.status == "active",
        ).all()
        
        core_assets = []
        for asset in assets:
            meta = asset.asset_meta or {}
            if meta.get("memory_level") == MemoryLevel.CORE:
                core_assets.append({
                    "asset_id": asset.asset_id,
                    "title": asset.title,
                    "content_snippet": asset.content[:200] + "..." if len(asset.content) > 200 else asset.content,
                    "usage_count": meta.get("usage_count", 0),
                    "last_used_at": meta.get("last_used_at"),
                })
        
        # 按使用次数排序
        core_assets.sort(key=lambda x: x["usage_count"], reverse=True)
        return core_assets[:limit]
    
    def get_archived_memory(self, limit: int = 20) -> List[dict]:
        """获取归档记忆"""
        assets = self.db.query(IPAsset).filter(
            IPAsset.ip_id == self.ip_id,
            IPAsset.status == "active",
        ).all()
        
        archived = []
        for asset in assets:
            meta = asset.asset_meta or {}
            if meta.get("memory_level") == MemoryLevel.ARCHIVE:
                archived.append({
                    "asset_id": asset.asset_id,
                    "title": asset.title,
                    "content_snippet": asset.content[:100] + "..." if len(asset.content) > 100 else asset.content,
                    "last_used_at": meta.get("last_used_at"),
                    "archived_at": meta.get("level_changed_at"),
                })
        
        return archived[:limit]
    
    def restore_from_archive(self, asset_id: str) -> bool:
        """从归档恢复记忆"""
        asset = self.db.query(IPAsset).filter(
            IPAsset.asset_id == asset_id,
            IPAsset.ip_id == self.ip_id,
        ).first()
        
        if not asset:
            return False
        
        meta = asset.asset_meta or {}
        meta["memory_level"] = MemoryLevel.ACTIVE
        meta["restored_at"] = datetime.utcnow().isoformat()
        
        asset.asset_meta = meta
        self.db.commit()
        
        return True
    
    def time_weighted_retrieval(
        self,
        query: str,
        top_k: int = 10,
        time_weight: float = 0.3,
    ) -> List[dict]:
        """
        时间加权检索
        最近使用的记忆权重更高
        """
        assets = self.db.query(IPAsset).filter(
            IPAsset.ip_id == self.ip_id,
            IPAsset.status == "active",
        ).all()
        
        now = datetime.utcnow()
        scored_assets = []
        
        for asset in assets:
            meta = asset.asset_meta or {}
            usage_count = meta.get("usage_count", 1)
            last_used = meta.get("last_used_at")
            
            # 计算时间衰减分数
            time_score = 1.0
            if last_used:
                try:
                    last_used_dt = datetime.fromisoformat(last_used)
                    days_ago = (now - last_used_dt).days
                    # 每天衰减5%，最低0.5
                    time_score = max(0.5, 1.0 - (days_ago * 0.05))
                except:
                    pass
            
            # 使用频率分数
            usage_score = min(1.0, usage_count / 5)
            
            # 记忆级别分数
            level = meta.get("memory_level", MemoryLevel.ACTIVE)
            level_score = {
                MemoryLevel.CORE: 1.0,
                MemoryLevel.ACTIVE: 0.7,
                MemoryLevel.ARCHIVE: 0.3,
            }.get(level, 0.5)
            
            # 综合分数
            final_score = (
                (1 - time_weight) * usage_score * level_score +
                time_weight * time_score
            )
            
            scored_assets.append({
                "asset_id": asset.asset_id,
                "title": asset.title,
                "content": asset.content,
                "score": final_score,
                "time_score": time_score,
                "usage_score": usage_score,
                "level": level,
            })
        
        # 排序
        scored_assets.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_assets[:top_k]


def consolidate_ip_memory(db: Session, ip_id: str) -> dict:
    """执行IP的记忆Consolidation"""
    engine = MemoryConsolidation(db, ip_id)
    return engine.consolidate()


def get_memory_summary(db: Session, ip_id: str) -> dict:
    """获取IP的记忆摘要"""
    engine = MemoryConsolidation(db, ip_id)
    
    stats = engine.get_memory_stats()
    core = engine.get_core_memory(limit=5)
    archived = engine.get_archived_memory(limit=5)
    
    return {
        "stats": stats,
        "core_memory": core,
        "archived_memory": archived,
    }
