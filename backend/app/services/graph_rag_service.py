"""
Graph RAG 服务 - 知识图谱构建与检索
基于 Neo4j 实现实体关系提取和图检索
"""
import json
import os
from typing import Any, List, Optional
from urllib.parse import urlparse

from neo4j import GraphDatabase

from app.config.neo4j_config import get_neo4j_config
from app.services.ai_client import chat, embed


def get_neo4j_driver():
    """获取Neo4j驱动"""
    config = get_neo4j_config()
    return GraphDatabase.driver(
        config["uri"],
        auth=(config["username"], config["password"]),
    )


def get_collection_name(ip_id: str) -> str:
    """Neo4j中IP对应的标签前缀"""
    return f"ip_{ip_id}"


# ==================== 实体关系提取 ====================

def extract_entities_from_text(text: str, ip_id: str) -> List[dict]:
    """
    使用LLM从文本中提取实体和关系
    返回格式: [{"type": "PERSON", "name": "xxx", "properties": {...}}, ...]
    """
    prompt = f"""从以下内容中提取实体和关系。

要求：
1. 识别人物(PERSON)、组织(ORGANIZATION)、地点(LOCATION)、概念(CONCEPT)、事件(EVENT)等实体
2. 识别实体之间的关系
3. 返回JSON数组格式

文本内容：
{text[:2000]}

返回格式（仅返回JSON，不要其他内容）：
[
  {{"type": "PERSON", "name": "人名", "properties": {{"role": "角色", "description": "描述"}}}},
  {{"type": "CONCEPT", "name": "概念名", "properties": {{"description": "描述"}}}},
  {{"type": "RELATION", "from": "实体A", "to": "实体B", "relation": "关系类型", "properties": {{"context": "上下文"}}}}
]
"""
    try:
        model = os.environ.get("LLM_MODEL") or None
        result_text = chat(
            messages=[
                {"role": "system", "content": "你是一个实体关系抽取专家。"},
                {"role": "user", "content": prompt},
            ],
            model=model,
        )
        if not result_text:
            return []
        # 尝试解析JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        entities = json.loads(result_text.strip())
        return entities
    except Exception as e:
        print(f"Entity extraction failed: {e}")
        return []


def build_knowledge_graph(
    ip_id: str,
    assets: List[dict],
    db_session=None,
) -> dict:
    """
    从素材构建知识图谱
    遍历每个素材，提取实体关系并写入Neo4j
    """
    config = get_neo4j_config()
    if not config["password"]:
        return {"error": "Neo4j not configured"}
    
    driver = get_neo4j_driver()
    
    entities_created = 0
    relations_created = 0
    errors = []
    
    try:
        with driver.session(database=config["database"]) as session:
            # 为每个素材提取实体关系
            for asset in assets:
                content = asset.get("content", "")
                if not content or len(content) < 50:
                    continue
                
                # 提取实体
                entities = extract_entities_from_text(content, ip_id)
                
                # 分离实体和关系
                node_entities = [e for e in entities if e.get("type") != "RELATION"]
                rel_entities = [e for e in entities if e.get("type") == "RELATION"]
                
                # 创建实体节点
                for entity in node_entities:
                    try:
                        entity_type = entity.get("type", "CONCEPT")
                        entity_name = entity.get("name", "")
                        properties = entity.get("properties", {})
                        
                        if not entity_name:
                            continue
                        
                        # 使用 MERGE 创建或更新节点
                        cypher = f"""
                        MERGE (e:`{entity_type}` {{name: $name}})
                        SET e.ip_id = $ip_id,
                            e.description = $description,
                            e.source_asset_id = $asset_id,
                            e.updated_at = datetime()
                        """
                        session.run(
                            cypher,
                            name=entity_name,
                            ip_id=ip_id,
                            description=properties.get("description", ""),
                            asset_id=asset.get("asset_id", ""),
                        )
                        entities_created += 1
                    except Exception as e:
                        errors.append(f"Entity error: {e}")
                
                # 创建关系
                for rel in rel_entities:
                    try:
                        from_entity = rel.get("from", "")
                        to_entity = rel.get("to", "")
                        relation_type = rel.get("relation", "RELATED_TO")
                        properties = rel.get("properties", {})
                        
                        if not from_entity or not to_entity:
                            continue
                        
                        cypher = f"""
                        MATCH (a {{name: $from_name, ip_id: $ip_id}})
                        MATCH (b {{name: $to_name, ip_id: $ip_id}})
                        MERGE (a)-[r:`{relation_type}`]->(b)
                        SET r.context = $context,
                            r.source_asset_id = $asset_id,
                            r.updated_at = datetime()
                        """
                        session.run(
                            cypher,
                            from_name=from_entity,
                            to_name=to_entity,
                            ip_id=ip_id,
                            context=properties.get("context", ""),
                            asset_id=asset.get("asset_id", ""),
                        )
                        relations_created += 1
                    except Exception as e:
                        errors.append(f"Relation error: {e}")
            
            return {
                "entities": entities_created,
                "relations": relations_created,
                "errors": errors[:10],
            }
    except Exception as e:
        return {"error": str(e)}
    finally:
        driver.close()


# ==================== 图检索 ====================

def graph_retrieve(
    ip_id: str,
    query: str,
    depth: int = 2,
    limit: int = 20,
) -> dict:
    """
    基于知识图谱的检索
    1. 将query转为向量，找到最相似的实体
    2. 扩展邻居节点
    3. 返回关联上下文
    """
    config = get_neo4j_config()
    if not config["password"]:
        return {"error": "Neo4j not configured", "nodes": [], "paths": []}
    
    driver = get_neo4j_driver()
    
    try:
        # 1. 找到与query相关的实体（简化：关键词匹配 + 向量相似）
        # 实际生产中可以用向量索引
        with driver.session(database=config["database"]) as session:
            # 查找包含query关键词的实体
            cypher = f"""
            MATCH (e {{ip_id: $ip_id}})
            WHERE e.name CONTAINS $query OR e.description CONTAINS $query
            RETURN e.name as name, labels(e)[0] as type, e.description as description
            LIMIT 10
            """
            result = session.run(cypher, ip_id=ip_id, query=query)
            seed_nodes = [dict(record) for record in result]
            
            if not seed_nodes:
                return {"nodes": [], "paths": [], "message": "未找到相关实体"}
            
            # 2. 扩展邻居（指定深度）
            node_ids = [n["name"] for n in seed_nodes]
            
            cypher_paths = f"""
            MATCH path = (start {{name: $start_name, ip_id: $ip_id}})-[{r}]->(end)
            WHERE r.ip_id = $ip_id OR r IS NULL
            WITH path, r, end
            LIMIT $limit
            RETURN 
                start.name as from,
                type(r) as relation,
                end.name as to,
                end.description as description,
                r.context as context
            """
            result = session.run(
                cypher_paths,
                start_name=node_ids[0],
                ip_id=ip_id,
                limit=limit,
            )
            
            paths = []
            for record in result:
                paths.append({
                    "from": record["from"],
                    "relation": record["relation"],
                    "to": record["to"],
                    "context": record.get("context", ""),
                })
            
            return {
                "seed_nodes": seed_nodes,
                "paths": paths,
            }
    except Exception as e:
        return {"error": str(e), "nodes": [], "paths": []}
    finally:
        driver.close()


def get_ip_graph_stats(ip_id: str) -> dict:
    """获取IP知识图谱统计信息"""
    config = get_neo4j_config()
    if not config["password"]:
        return {"error": "Neo4j not configured"}
    
    driver = get_neo4j_driver()
    
    try:
        with driver.session(database=config["database"]) as session:
            # 统计节点数
            cypher_nodes = f"""
            MATCH (n {{ip_id: $ip_id}})
            RETURN labels(n)[0] as type, count(*) as count
            """
            result = session.run(cypher_nodes, ip_id=ip_id)
            node_counts = {record["type"]: record["count"] for record in result}
            
            # 统计关系数
            cypher_rels = f"""
            MATCH ()-[r]->() 
            WHERE r.ip_id = $ip_id
            RETURN type(r) as type, count(*) as count
            """
            result = session.run(cypher_rels, ip_id=ip_id)
            rel_counts = {record["type"]: record["count"] for record in result}
            
            return {
                "nodes": node_counts,
                "relations": rel_counts,
                "total_nodes": sum(node_counts.values()),
                "total_relations": sum(rel_counts.values()),
            }
    except Exception as e:
        return {"error": str(e)}
    finally:
        driver.close()


def clear_ip_graph(ip_id: str) -> dict:
    """清除IP的知识图谱（危险操作）"""
    config = get_neo4j_config()
    if not config["password"]:
        return {"error": "Neo4j not configured"}
    
    driver = get_neo4j_driver()
    
    try:
        with driver.session(database=config["database"]) as session:
            # 删除该IP的所有节点和关系
            cypher = f"""
            MATCH (n {{ip_id: $ip_id}})
            DETACH DELETE n
            """
            session.run(cypher, ip_id=ip_id)
            return {"success": True, "message": f"已清除 IP {ip_id} 的知识图谱"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        driver.close()
