"""
本地缓存层
- 解耦外部数据源依赖
- 支持缓存预热
- 多级缓存策略
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

from .base import TopicData

logger = logging.getLogger(__name__)


class TopicCache:
    """
    话题数据缓存
    
    设计要点：
    1. 按IP+数据源维度缓存
    2. 支持TTL自动过期
    3. 磁盘+内存二级缓存
    4. 缓存预热机制
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(__file__).resolve().parents[3] / ".cache" / "topics"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
    
    def _get_cache_key(self, ip_id: str, source_id: str) -> str:
        """生成缓存key"""
        return hashlib.md5(f"{ip_id}:{source_id}".encode()).hexdigest()[:16]
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"
    
    def get(
        self, 
        ip_id: str, 
        source_id: str, 
        max_age_hours: int = 24
    ) -> Optional[List[TopicData]]:
        """
        获取缓存数据
        
        Args:
            ip_id: IP ID
            source_id: 数据源ID
            max_age_hours: 最大缓存时间
            
        Returns:
            缓存的话题列表，过期返回None
        """
        cache_key = self._get_cache_key(ip_id, source_id)
        
        # 先查内存
        if cache_key in self._memory_cache:
            cache_entry = self._memory_cache[cache_key]
            if self._is_valid(cache_entry, max_age_hours):
                logger.debug(f"[Cache] Memory hit for {ip_id}/{source_id}")
                return self._deserialize_topics(cache_entry["data"])
        
        # 再查磁盘
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                cache_entry = json.loads(cache_path.read_text(encoding="utf-8"))
                if self._is_valid(cache_entry, max_age_hours):
                    # 写入内存缓存
                    self._memory_cache[cache_key] = cache_entry
                    logger.debug(f"[Cache] Disk hit for {ip_id}/{source_id}")
                    return self._deserialize_topics(cache_entry["data"])
            except Exception as e:
                logger.warning(f"[Cache] Failed to read cache: {e}")
        
        return None
    
    def set(
        self, 
        ip_id: str, 
        source_id: str, 
        topics: List[TopicData]
    ):
        """
        设置缓存
        
        Args:
            ip_id: IP ID
            source_id: 数据源ID
            topics: 话题列表
        """
        cache_key = self._get_cache_key(ip_id, source_id)
        
        cache_entry = {
            "created_at": datetime.now().isoformat(),
            "ip_id": ip_id,
            "source_id": source_id,
            "count": len(topics),
            "data": self._serialize_topics(topics)
        }
        
        # 写入内存
        self._memory_cache[cache_key] = cache_entry
        
        # 写入磁盘
        try:
            cache_path = self._get_cache_path(cache_key)
            cache_path.write_text(
                json.dumps(cache_entry, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"[Cache] Failed to write cache: {e}")
    
    def invalidate(self, ip_id: Optional[str] = None, source_id: Optional[str] = None):
        """
        使缓存失效
        
        Args:
            ip_id: 指定IP，None表示所有
            source_id: 指定数据源，None表示所有
        """
        # 清理内存缓存
        if ip_id is None and source_id is None:
            self._memory_cache.clear()
        else:
            keys_to_remove = []
            for key, entry in self._memory_cache.items():
                match = True
                if ip_id and entry.get("ip_id") != ip_id:
                    match = False
                if source_id and entry.get("source_id") != source_id:
                    match = False
                if match:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._memory_cache[key]
        
        # 清理磁盘缓存
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                if ip_id is None and source_id is None:
                    cache_file.unlink()
                else:
                    try:
                        entry = json.loads(cache_file.read_text(encoding="utf-8"))
                        match = True
                        if ip_id and entry.get("ip_id") != ip_id:
                            match = False
                        if source_id and entry.get("source_id") != source_id:
                            match = False
                        if match:
                            cache_file.unlink()
                    except:
                        pass
        except Exception as e:
            logger.warning(f"[Cache] Failed to invalidate cache: {e}")
    
    def _is_valid(self, cache_entry: Dict, max_age_hours: int) -> bool:
        """检查缓存是否有效"""
        try:
            created_at = datetime.fromisoformat(cache_entry["created_at"])
            age = datetime.now() - created_at
            return age < timedelta(hours=max_age_hours)
        except:
            return False
    
    def _serialize_topics(self, topics: List[TopicData]) -> List[Dict]:
        """序列化话题"""
        result = []
        for t in topics:
            data = {
                "id": t.id,
                "title": t.title,
                "original_title": t.original_title,
                "platform": t.platform,
                "url": t.url,
                "tags": t.tags,
                "score": t.score,
                "likes": t.likes,
                "comments": t.comments,
                "shares": t.shares,
                "author_followers": t.author_followers,
                "publish_time": t.publish_time.isoformat() if t.publish_time else None,
                "source": t.source,
                "extra": t.extra,
            }
            result.append(data)
        return result
    
    def _deserialize_topics(self, data: List[Dict]) -> List[TopicData]:
        """反序列化话题"""
        result = []
        for d in data:
            topic = TopicData(
                id=d["id"],
                title=d["title"],
                original_title=d["original_title"],
                platform=d["platform"],
                url=d["url"],
                tags=d["tags"],
                score=d["score"],
                likes=d.get("likes", 0),
                comments=d.get("comments", 0),
                shares=d.get("shares", 0),
                author_followers=d.get("author_followers", 0),
                publish_time=datetime.fromisoformat(d["publish_time"]) if d.get("publish_time") else None,
                source=d.get("source", ""),
                extra=d.get("extra", {})
            )
            result.append(topic)
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        disk_count = len(list(self.cache_dir.glob("*.json")))
        memory_count = len(self._memory_cache)
        
        return {
            "disk_entries": disk_count,
            "memory_entries": memory_count,
            "cache_dir": str(self.cache_dir)
        }
