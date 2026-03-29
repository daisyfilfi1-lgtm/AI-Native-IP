"""
混合检索服务 - 向量检索 + Graph RAG 融合
结合向量语义理解和图关系推理，提供更精准的检索结果
"""
import os
from typing import Any, Dict, List, Optional

from app.services.ai_client import embed
from app.services.graph_rag_service import graph_retrieve
from app.services.vector_service_qdrant import query_similar_assets


class HybridRetrievalConfig:
    """混合检索配置"""
    
    # 权重配置（可动态调整）
    VECTOR_WEIGHT = 0.6      # 向量检索权重
    GRAPH_WEIGHT = 0.4       # Graph RAG权重
    
    # 向量检索配置
    VECTOR_TOP_K = 20        # 向量检索返回数量
    
    # Graph检索配置
    GRAPH_DEPTH = 2          # 图扩展深度
    GRAPH_TOP_K = 10         # Graph返回数量
    
    # 结果融合配置
    MIN_SCORE_THRESHOLD = 0.3  # 最低分数阈值
    ENABLE_RRF = True        # 使用RRF融合


def _reciprocal_rank_fusion(
    vector_results: List[dict],
    graph_results: List[dict],
    k: int = 60,
) -> List[dict]:
    """
    倒数排名融合（RRF）
    将多个排名列表融合为一个综合排名
    """
    # 构建向量结果排名
    vector_rank = {}
    for i, r in enumerate(vector_results):
        asset_id = r.get("asset_id")
        if asset_id:
            vector_rank[asset_id] = {
                "rank": i + 1,
                "score": r.get("similarity", 0),
                "source": "vector",
                "content": r.get("content", ""),
                "metadata": r.get("metadata", {}),
            }
    
    # 构建图结果排名
    graph_rank = {}
    for i, r in enumerate(graph_results):
        # Graph结果可能是实体名或asset_id
        paths = r.get("paths", [])
        for path in paths:
            # 从关系路径中提取相关asset
            from_node = path.get("from", "")
            to_node = path.get("to", "")
            
            # 简化：使用节点名作为匹配key
            for node in [from_node, to_node]:
                if node and node not in graph_rank:
                    graph_rank[node] = {
                        "rank": i + 1,
                        "score": 1.0 / (i + 1),  # 使用1/(rank)作为图分数
                        "source": "graph",
                        "context": path.get("context", ""),
                        "relation": path.get("relation", ""),
                    }
    
    # RRF融合
    rrf_scores = {}
    all_keys = set(vector_rank.keys()) | set(graph_rank.keys())
    
    for key in all_keys:
        score = 0.0
        
        if key in vector_rank:
            score += 1.0 / (k + vector_rank[key]["rank"])
        
        if key in graph_rank:
            score += 1.0 / (k + graph_rank[key]["rank"])
        
        rrf_scores[key] = score
    
    # 排序
    sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    
    # 构建融合结果
    results = []
    for key in sorted_keys[:20]:  # 返回top 20
        result = {
            "asset_id": key,
            "hybrid_score": rrf_scores[key],
            "sources": [],
        }
        
        if key in vector_rank:
            result["sources"].append("vector")
            result["vector_score"] = vector_rank[key]["score"]
            result["vector_rank"] = vector_rank[key]["rank"]
            result["content"] = vector_rank[key].get("content", "")
            result["metadata"] = vector_rank[key].get("metadata", {})
        
        if key in graph_rank:
            result["sources"].append("graph")
            result["graph_score"] = graph_rank[key]["score"]
            result["graph_rank"] = graph_rank[key]["rank"]
            result["graph_context"] = graph_rank[key].get("context", "")
            result["relation"] = graph_rank[key].get("relation", "")
        
        # 计算加权分数
        vector_s = result.get("vector_score", 0)
        graph_s = result.get("graph_score", 0)
        
        # 归一化到0-1
        if result["sources"] == ["vector"]:
            result["weighted_score"] = vector_s * HybridRetrievalConfig.VECTOR_WEIGHT
        elif result["sources"] == ["graph"]:
            result["weighted_score"] = graph_s * HybridRetrievalConfig.GRAPH_WEIGHT
        else:
            # 两个来源都有
            vec_norm = vector_s  # 假设向量分数已在0-1
            graph_norm = min(graph_s * 5, 1.0)  # 放大graph分数
            result["weighted_score"] = (
                vec_norm * HybridRetrievalConfig.VECTOR_WEIGHT +
                graph_norm * HybridRetrievalConfig.GRAPH_WEIGHT
            )
        
        results.append(result)
    
    # 过滤低分结果
    results = [r for r in results if r["weighted_score"] >= HybridRetrievalConfig.MIN_SCORE_THRESHOLD]
    
    return results


def _expand_graph_to_assets(
    graph_results: List[dict],
    db,
    ip_id: str,
) -> List[dict]:
    """
    将Graph检索结果转换为asset格式
    通过实体名匹配到实际素材
    """
    from app.db.models import IPAsset
    
    # 提取所有实体名
    entity_names = set()
    for gr in graph_results:
        seed_nodes = gr.get("seed_nodes", [])
        for node in seed_nodes:
            entity_names.add(node.get("name", ""))
        
        paths = gr.get("paths", [])
        for path in paths:
            entity_names.add(path.get("from", ""))
            entity_names.add(path.get("to", ""))
    
    if not entity_names:
        return []
    
    # 在素材中搜索包含这些实体的内容
    assets = db.query(IPAsset).filter(
        IPAsset.ip_id == ip_id,
        IPAsset.status == "active",
    ).all()
    
    # 匹配包含实体名的素材
    matched_assets = []
    for asset in assets:
        content = asset.content or ""
        for entity in entity_names:
            if entity and entity.lower() in content.lower():
                matched_assets.append({
                    "asset_id": asset.asset_id,
                    "similarity": 0.8,  # 简化：固定分数
                    "content": content[:500],
                    "metadata": asset.asset_meta or {},
                    "matched_entity": entity,
                    "source": "graph_expanded",
                })
                break
    
    # 去重并限制数量
    seen = set()
    unique_assets = []
    for a in matched_assets:
        if a["asset_id"] not in seen:
            seen.add(a["asset_id"])
            unique_assets.append(a)
    
    return unique_assets[:HybridRetrievalConfig.GRAPH_TOP_K]


def hybrid_search(
    db,
    ip_id: str,
    query: str,
    vector_weight: float = None,
    graph_weight: float = None,
    top_k: int = 10,
    use_vector: bool = True,
    use_graph: bool = True,
) -> dict:
    """
    混合检索 - 向量 + Graph RAG 融合
    
    参数:
        db: 数据库会话
        ip_id: IP ID
        query: 检索query
        vector_weight: 向量权重（覆盖默认）
        graph_weight: 图权重（覆盖默认）
        top_k: 返回结果数
        use_vector: 是否使用向量检索
        use_graph: 是否使用图检索
    
    返回:
        {
            "query": str,
            "total": int,
            "results": [...],
            "vector_results_count": int,
            "graph_results_count": int,
            "fusion_method": "RRF",
        }
    """
    # 更新配置
    if vector_weight is not None:
        HybridRetrievalConfig.VECTOR_WEIGHT = vector_weight
    if graph_weight is not None:
        HybridRetrievalConfig.GRAPH_WEIGHT = graph_weight
    
    # 确保权重和为1
    total_weight = HybridRetrievalConfig.VECTOR_WEIGHT + HybridRetrievalConfig.GRAPH_WEIGHT
    if total_weight != 1.0:
        HybridRetrievalConfig.VECTOR_WEIGHT /= total_weight
        HybridRetrievalConfig.GRAPH_WEIGHT /= total_weight
    
    vector_results = []
    
    # 1. 向量检索
    if use_vector:
        try:
            vector_results = query_similar_assets(
                db,
                ip_id=ip_id,
                query=query,
                top_k=HybridRetrievalConfig.VECTOR_TOP_K,
            )
        except Exception as e:
            print(f"Vector search failed: {e}")
    
    # 2. Graph检索（graph_retrieve 返回单 dict；RRF 需要「每条带 paths 的记录」列表）
    graph_results: Any = {}
    graph_expanded: List[dict] = []
    if use_graph:
        try:
            graph_results = graph_retrieve(
                ip_id=ip_id,
                query=query,
                depth=HybridRetrievalConfig.GRAPH_DEPTH,
                limit=HybridRetrievalConfig.GRAPH_TOP_K,
            )
            
            # 将Graph结果转换为asset格式
            if graph_results and not graph_results.get("error"):
                graph_expanded = _expand_graph_to_assets([graph_results], db, ip_id)
            else:
                graph_expanded = []
        except Exception as e:
            print(f"Graph search failed: {e}")
            graph_results = {}
            graph_expanded = []

    graph_list_for_rrf: List[dict] = []
    if isinstance(graph_results, dict) and graph_results and not graph_results.get("error"):
        graph_list_for_rrf = [graph_results]
    
    # 3. 结果融合
    if use_vector and use_graph:
        # 纯向量+纯图结果融合
        fused_results = _reciprocal_rank_fusion(vector_results, graph_list_for_rrf)
        
        # 添加graph扩展的结果
        for ge in graph_expanded:
            # 检查是否已存在
            existing_ids = [r.get("asset_id") for r in fused_results]
            if ge["asset_id"] not in existing_ids:
                ge["hybrid_score"] = ge["similarity"] * HybridRetrievalConfig.GRAPH_WEIGHT
                ge["sources"] = ["graph_expanded"]
                fused_results.append(ge)
        
        # 按混合分数排序
        fused_results.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
        final_results = fused_results[:top_k]
        
    elif use_vector:
        final_results = [
            {
                **r,
                "hybrid_score": r.get("similarity", 0),
                "sources": ["vector"],
            }
            for r in vector_results[:top_k]
        ]
    
    elif use_graph:
        final_results = graph_expanded[:top_k]
        for r in final_results:
            r["sources"] = ["graph_expanded"]
            r["hybrid_score"] = r.get("similarity", 0) * HybridRetrievalConfig.GRAPH_WEIGHT
    
    else:
        final_results = []
    
    return {
        "query": query,
        "ip_id": ip_id,
        "total": len(final_results),
        "results": final_results,
        "config": {
            "vector_weight": HybridRetrievalConfig.VECTOR_WEIGHT,
            "graph_weight": HybridRetrievalConfig.GRAPH_WEIGHT,
            "vector_results_count": len(vector_results),
            "graph_results_count": len(graph_list_for_rrf) if use_graph else 0,
            "fusion_method": "RRF",
        },
    }


def set_hybrid_weights(vector_weight: float, graph_weight: float):
    """动态调整混合检索权重"""
    HybridRetrievalConfig.VECTOR_WEIGHT = vector_weight
    HybridRetrievalConfig.GRAPH_WEIGHT = graph_weight
