"""
Neo4j 知识图谱配置
"""
import os
from typing import Any, Optional


def get_neo4j_config() -> dict[str, Any]:
    """
    返回 Neo4j 配置
    """
    return {
        "uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687").strip(),
        "username": os.environ.get("NEO4J_USERNAME", "neo4j").strip(),
        "password": os.environ.get("NEO4J_PASSWORD", "").strip(),
        "database": os.environ.get("NEO4J_DATABASE", "neo4j").strip(),
    }


def is_neo4j_configured() -> bool:
    """检查Neo4j是否已配置"""
    config = get_neo4j_config()
    return bool(config["uri"] and config["password"])
