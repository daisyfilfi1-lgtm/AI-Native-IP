"""
Graph RAG 路由 - 知识图谱API
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP, IPAsset
from app.services.graph_rag_service import (
    build_knowledge_graph,
    clear_ip_graph,
    get_ip_graph_stats,
    graph_retrieve,
)
from app.services.memory_config_service import get_ip as get_ip_model

router = APIRouter()


class GraphBuildRequest(BaseModel):
    ip_id: str
    force_rebuild: bool = Field(False, description="强制重建（先清除现有图谱）")


class GraphBuildResponse(BaseModel):
    entities: int
    relations: int
    errors: list


class GraphRetrieveRequest(BaseModel):
    ip_id: str
    query: str
    depth: Optional[int] = 2
    limit: Optional[int] = 20


class GraphRetrieveResponse(BaseModel):
    seed_nodes: list
    paths: list
    message: Optional[str] = None


class GraphStatsResponse(BaseModel):
    nodes: dict
    relations: dict
    total_nodes: int
    total_relations: int


@router.post("/graph/build", response_model=GraphBuildResponse)
def build_graph(
    payload: GraphBuildRequest,
    db: Session = Depends(get_db),
):
    """从IP的素材构建知识图谱"""
    if not get_ip_model(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    
    # 获取该IP的所有素材
    assets = db.query(IPAsset).filter(
        IPAsset.ip_id == payload.ip_id,
        IPAsset.status == "active",
    ).all()
    
    if not assets:
        raise HTTPException(status_code=400, detail="该IP没有素材，请先同步知识库")
    
    asset_dicts = [
        {
            "asset_id": a.asset_id,
            "content": a.content,
            "title": a.title,
        }
        for a in assets
    ]
    
    # 构建图谱
    result = build_knowledge_graph(
        ip_id=payload.ip_id,
        assets=asset_dicts,
    )
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return GraphBuildResponse(
        entities=result.get("entities", 0),
        relations=result.get("relations", 0),
        errors=result.get("errors", []),
    )


@router.post("/graph/retrieve", response_model=GraphRetrieveResponse)
def retrieve_graph(
    payload: GraphRetrieveRequest,
    db: Session = Depends(get_db),
):
    """基于知识图谱检索"""
    if not get_ip_model(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    
    result = graph_retrieve(
        ip_id=payload.ip_id,
        query=payload.query,
        depth=payload.depth or 2,
        limit=payload.limit or 20,
    )
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return GraphRetrieveResponse(
        seed_nodes=result.get("seed_nodes", []),
        paths=result.get("paths", []),
        message=result.get("message"),
    )


@router.get("/graph/stats/{ip_id}", response_model=GraphStatsResponse)
def get_graph_stats(
    ip_id: str,
    db: Session = Depends(get_db),
):
    """获取知识图谱统计"""
    if not get_ip_model(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    
    result = get_ip_graph_stats(ip_id)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return GraphStatsResponse(
        nodes=result.get("nodes", {}),
        relations=result.get("relations", {}),
        total_nodes=result.get("total_nodes", 0),
        total_relations=result.get("total_relations", 0),
    )


@router.delete("/graph/{ip_id}")
def delete_graph(
    ip_id: str,
    db: Session = Depends(get_db),
):
    """删除知识图谱（危险操作）"""
    if not get_ip_model(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    
    result = clear_ip_graph(ip_id)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result
