"""
Qdrant 向量库管理路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import IP
from app.services.memory_config_service import get_ip as get_ip_model
from app.services.vector_service_qdrant import (
    delete_collection,
    delete_asset_vector,
    get_collection_info,
    query_similar_assets,
)

router = APIRouter()


class VectorSearchRequest(BaseModel):
    ip_id: str
    query: str
    top_k: Optional[int] = 10
    use_hybrid: Optional[bool] = True


class VectorSearchResponse(BaseModel):
    results: list


class CollectionInfoResponse(BaseModel):
    info: dict


@router.post("/vector/search", response_model=VectorSearchResponse)
def search_vectors(
    payload: VectorSearchRequest,
    db: Session = Depends(get_db),
):
    """向量检索接口 - 使用Qdrant"""
    if not get_ip_model(db, payload.ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {payload.ip_id}")
    
    results = query_similar_assets(
        db,
        ip_id=payload.ip_id,
        query=payload.query,
        top_k=payload.top_k or 10,
        use_hybrid=payload.use_hybrid if payload.use_hybrid is not None else True,
    )
    
    return VectorSearchResponse(results=results)


@router.get("/vector/collection/{ip_id}", response_model=CollectionInfoResponse)
def get_collection(
    ip_id: str,
    db: Session = Depends(get_db),
):
    """获取IP的向量Collection信息"""
    if not get_ip_model(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    
    info = get_collection_info(ip_id)
    return CollectionInfoResponse(info=info)


@router.delete("/vector/collection/{ip_id}")
def delete_ip_collection(
    ip_id: str,
    db: Session = Depends(get_db),
):
    """删除IP的所有向量（危险操作）"""
    if not get_ip_model(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    
    success = delete_collection(ip_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    
    return {"success": True, "message": f"已删除 IP {ip_id} 的所有向量"}


@router.delete("/vector/asset/{asset_id}")
def delete_vector(
    asset_id: str,
    ip_id: str,
    db: Session = Depends(get_db),
):
    """删除单个向量"""
    if not get_ip_model(db, ip_id):
        raise HTTPException(status_code=404, detail=f"IP 不存在: {ip_id}")
    
    success = delete_asset_vector(db, asset_id=asset_id, ip_id=ip_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    
    return {"success": True}
