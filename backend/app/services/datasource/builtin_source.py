"""
内置数据源 - 零依赖的兜底数据源

设计要点：
1. 完全零外部依赖
2. 按IP维度组织
3. 支持YAML/JSON配置
4. 热更新支持
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

from .base import DataSource, DataSourceConfig, TopicData, DataSourcePriority

logger = logging.getLogger(__name__)


class BuiltinDataSource(DataSource):
    """
    内置数据源
    
    从本地配置文件加载爆款选题，不依赖任何外部服务。
    作为最高优先级的兜底数据源。
    """
    
    def __init__(self, config: Optional[DataSourceConfig] = None):
        if config is None:
            config = DataSourceConfig(
                source_id="builtin",
                name="内置爆款库",
                priority=DataSourcePriority.P3,
                enabled=True,
                max_results=50
            )
        super().__init__(config)
        
        # 配置文件路径
        self.config_file = Path(__file__).resolve().parents[3] / "config" / "builtin_topics.yaml"
        self._topics_db: Dict[str, Dict[str, List[Dict]]] = {}
        self._last_load: Optional[datetime] = None
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """加载内置选题配置"""
        # 如果配置文件存在，从文件加载
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._topics_db = yaml.safe_load(f) or {}
                self._last_load = datetime.now()
                logger.info(f"[BuiltinSource] Loaded {len(self._topics_db)} IP configs from {self.config_file}")
                return
            except Exception as e:
                logger.warning(f"[BuiltinSource] Failed to load config file: {e}, using default")
        
        # 使用默认配置
        self._topics_db = self._get_default_config()
        self._last_load = datetime.now()
        logger.info(f"[BuiltinSource] Using default config with {len(self._topics_db)} IPs")
    
    def _get_default_config(self) -> Dict[str, Dict[str, List[Dict]]]:
        """获取默认配置"""
        return {
            "xiaomin1": {
                "money": [
                    {
                        "id": "builtin_money_001",
                        "title": "2000块启动资金，我是如何做到月入3万的",
                        "tags": ["低成本创业", "宝妈副业", "月入3万"],
                        "score": 4.95,
                        "viral_elements": ["cost", "top", "contrast"],
                    },
                    {
                        "id": "builtin_money_002",
                        "title": "宝妈摆摊第30天，终于突破日入1000",
                        "tags": ["宝妈创业", "摆摊", "日入1000"],
                        "score": 4.90,
                    },
                    {
                        "id": "builtin_money_003",
                        "title": "从负债10万到月入5万，我只用了这一招",
                        "tags": ["负债翻身", "月入5万", "商业思维"],
                        "score": 4.92,
                    },
                    {
                        "id": "builtin_money_004",
                        "title": "私域变现的真相：90%的人都做错了这一步",
                        "tags": ["私域", "变现", "避坑"],
                        "score": 4.85,
                    },
                    {
                        "id": "builtin_money_005",
                        "title": "不想上班？试试这个低成本副业，宝妈实测月入过万",
                        "tags": ["副业", "低成本", "月入过万"],
                        "score": 4.88,
                    },
                ],
                "emotion": [
                    {
                        "id": "builtin_emotion_001",
                        "title": "32岁离婚带俩娃，我是怎么靠自己走出低谷的",
                        "tags": ["离婚", "带娃", "逆袭"],
                        "score": 4.94,
                    },
                    {
                        "id": "builtin_emotion_002",
                        "title": "婆婆说我带娃不赚钱，现在我月入3万她闭嘴了",
                        "tags": ["婆媳", "带娃", "月入3万"],
                        "score": 4.91,
                    },
                    {
                        "id": "builtin_emotion_003",
                        "title": "老公说我不务正业，现在月入2万他闭嘴了",
                        "tags": ["宝妈", "创业", "夫妻"],
                        "score": 4.93,
                    },
                    {
                        "id": "builtin_emotion_004",
                        "title": "当妈妈后我才明白：经济独立比啥都重要",
                        "tags": ["宝妈", "经济独立", "女性成长"],
                        "score": 4.84,
                    },
                ],
                "skill": [
                    {
                        "id": "builtin_skill_001",
                        "title": "这个馒头配方我练了3年，今天免费分享",
                        "tags": ["馒头", "配方", "教学"],
                        "score": 4.88,
                    },
                    {
                        "id": "builtin_skill_002",
                        "title": "私房爆款的秘密：从揉面到造型的完整教程",
                        "tags": ["私房", "爆款", "教程"],
                        "score": 4.85,
                    },
                    {
                        "id": "builtin_skill_003",
                        "title": "2000元起步：她用一手馒头绝活做到月入5万",
                        "tags": ["低成本", "馒头", "绝活"],
                        "score": 4.90,
                    },
                ],
                "life": [
                    {
                        "id": "builtin_life_001",
                        "title": "创业后的我，终于活成了自己想要的样子",
                        "tags": ["创业", "女性", "精致生活"],
                        "score": 4.80,
                    },
                    {
                        "id": "builtin_life_002",
                        "title": "又美又飒：创业宝妈的精致日常",
                        "tags": ["宝妈", "创业", "精致"],
                        "score": 4.78,
                    },
                ],
            },
            "default": {
                "money": [
                    {"id": "default_money_001", "title": "月入过万的秘密：这个方法90%的人都不知道", "tags": ["赚钱", "副业"], "score": 4.8},
                    {"id": "default_money_002", "title": "从0到月入3万：普通人的可复制路径", "tags": ["创业", "变现"], "score": 4.75},
                ],
                "emotion": [
                    {"id": "default_emotion_001", "title": "成年人最大的体面：拥有说不的能力", "tags": ["成长", "独立"], "score": 4.75},
                ],
                "skill": [
                    {"id": "default_skill_001", "title": "这个技巧我练了100遍，今天分享给你", "tags": ["技巧", "教学"], "score": 4.7},
                ],
            }
        }
    
    def is_available(self) -> bool:
        """内置数据源始终可用"""
        return True
    
    async def fetch(self, ip_profile: Dict[str, Any], limit: int) -> List[TopicData]:
        """
        获取内置选题
        
        按4-3-2-1内容矩阵分配
        """
        ip_id = ip_profile.get("ip_id", "default")
        
        # 获取该IP的选题库
        topics_db = self._topics_db.get(ip_id, self._topics_db.get("default", {}))
        
        # 按矩阵比例分配
        matrix = {
            "money": int(limit * 0.4),
            "emotion": int(limit * 0.3),
            "skill": int(limit * 0.2),
            "life": max(1, limit - int(limit * 0.4) - int(limit * 0.3) - int(limit * 0.2)),
        }
        
        result = []
        for content_type, count in matrix.items():
            type_topics = topics_db.get(content_type, [])
            for t in type_topics[:count]:
                topic = TopicData(
                    id=t.get("id", ""),
                    title=t.get("title", ""),
                    original_title=t.get("title", ""),
                    platform="builtin",
                    url="",
                    tags=t.get("tags", []),
                    score=t.get("score", 4.0),
                    source="builtin",
                    extra={
                        "content_type": content_type,
                        "viral_elements": t.get("viral_elements", []),
                    }
                )
                result.append(topic)
        
        # 随机打乱
        import random
        random.shuffle(result)
        
        logger.info(f"[BuiltinSource] Returned {len(result)} topics for {ip_id}")
        return result[:limit]
    
    def reload(self):
        """热重载配置"""
        self._load_config()
    
    def add_topics(self, ip_id: str, content_type: str, topics: List[Dict]):
        """
        动态添加选题
        
        用于运营后台动态更新内置库
        """
        if ip_id not in self._topics_db:
            self._topics_db[ip_id] = {}
        
        if content_type not in self._topics_db[ip_id]:
            self._topics_db[ip_id][content_type] = []
        
        self._topics_db[ip_id][content_type].extend(topics)
        
        # 保存到文件
        self._save_config()
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(self._topics_db, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            logger.error(f"[BuiltinSource] Failed to save config: {e}")
