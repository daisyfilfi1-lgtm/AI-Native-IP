"""
异步补齐向量任务脚本

用途：
- 当 INGEST_SKIP_EMBEDDING=true 时，ingest只保存文本
- 本脚本用于后台批量补齐缺失的向量

用法：
    # 单次运行
    python scripts/backfill_vectors.py

    # Railway Cron 定时任务（每5分钟）
    # 配置: python scripts/backfill_vectors.py

环境变量：
    BACKFILL_BATCH_SIZE=50    # 每批处理数量
    BACKFILL_IP_ID=           # 可选：只处理特定IP
"""
import os
import sys
import logging
import argparse

# 添加项目根目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.env_loader import load_backend_env
load_backend_env()

from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.db.models import IPAsset, AssetVector
from app.services.vector_service import upsert_asset_vector
from app.services.ai_client import embed_texts_batched

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_batch_size() -> int:
    raw = os.environ.get("BACKFILL_BATCH_SIZE", "").strip()
    if raw:
        try:
            return max(10, min(100, int(raw)))
        except ValueError:
            pass
    return 50


def find_assets_without_vectors(db, ip_id: str = None, limit: int = 50):
    """
    找出没有向量的资产
    
    逻辑：IPAsset存在，但AssetVector中没有对应记录
    """
    # 子查询：已有向量的asset_id
    existing = select(AssetVector.asset_id).distinct()
    
    # 主查询：ip_assets中不在上述子查询中的记录
    stmt = (
        select(IPAsset)
        .where(IPAsset.asset_id.not_in(existing))
        .where(IPAsset.status == "active")
        .where(IPAsset.content.isnot(None))
        .where(IPAsset.content != "")
    )
    
    if ip_id:
        stmt = stmt.where(IPAsset.ip_id == ip_id)
    
    stmt = stmt.limit(limit)
    
    return db.execute(stmt).scalars().all()


def backfill_vectors(ip_id: str = None, batch_size: int = None):
    """
    批量补齐缺失的向量
    """
    batch_size = batch_size or get_batch_size()
    
    db = SessionLocal()
    try:
        # 找出缺失向量的资产
        assets = find_assets_without_vectors(db, ip_id, batch_size)
        
        if not assets:
            logger.info("没有需要补齐向量的资产")
            return 0
        
        logger.info(f"找到 {len(assets)} 个需要补齐向量的资产")
        
        # 批量提取文本
        texts = []
        asset_ids = []
        for asset in assets:
            content = (asset.content or "").strip()
            if content:
                texts.append(content[:10000])  # 截断超长内容
                asset_ids.append(asset.asset_id)
        
        if not texts:
            logger.info("没有有效文本内容")
            return 0
        
        # 批量计算向量
        logger.info(f"正在计算 {len(texts)} 个向量...")
        embeddings = embed_texts_batched(texts, batch_size=min(16, len(texts)))
        
        if not embeddings:
            logger.error("向量计算失败")
            return 0
        
        # 逐个写入向量
        success_count = 0
        for i, asset_id in enumerate(asset_ids):
            try:
                emb = embeddings[i] if i < len(embeddings) else None
                if emb:
                    # 获取对应的asset
                    asset = db.query(IPAsset).filter(IPAsset.asset_id == asset_id).first()
                    if asset:
                        upsert_asset_vector(
                            db,
                            asset_id=asset_id,
                            ip_id=asset.ip_id,
                            content=asset.content,
                            precomputed_embedding=emb,
                        )
                        success_count += 1
            except Exception as e:
                logger.warning(f"写入向量失败 {asset_id}: {e}")
        
        db.commit()
        logger.info(f"成功补齐 {success_count}/{len(asset_ids)} 个向量")
        return success_count
        
    except Exception as e:
        logger.exception(f"补齐向量失败: {e}")
        db.rollback()
        return 0
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="异步补齐缺失的向量")
    parser.add_argument("--ip-id", "-i", help="只处理指定IP的资产")
    parser.add_argument("--batch-size", "-b", type=int, help="每批处理数量")
    parser.add_argument("--dry-run", "-n", action="store_true", help="只检查不执行")
    
    args = parser.parse_args()
    
    if args.dry_run:
        db = SessionLocal()
        try:
            assets = find_assets_without_vectors(db, args.ip_id, 100)
            logger.info(f"dry-run: 发现 {len(assets)} 个需要补齐的资产")
        finally:
            db.close()
        return
    
    count = backfill_vectors(args.ip_id, args.batch_size)
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
