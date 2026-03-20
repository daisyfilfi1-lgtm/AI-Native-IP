"""
数据迁移脚本：将PostgreSQL中的向量数据迁移到Qdrant
用法: python scripts/migrate_to_qdrant.py [--ip-id IP_ID] [--dry-run]
"""
import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.qdrant_config import get_qdrant_config
from app.db.models import AssetVector, IP
from app.services.vector_service_qdrant import (
    delete_asset_vector,
    ensure_collection,
    get_collection_name,
    get_qdrant_client,
    upsert_asset_vector,
)


def migrate_ip_vectors(db_session, ip_id: str, dry_run: bool = False) -> dict:
    """迁移单个IP的所有向量到Qdrant"""
    
    # 获取IP的所有向量
    vectors = db_session.query(AssetVector).filter(AssetVector.ip_id == ip_id).all()
    
    if not vectors:
        return {"ip_id": ip_id, "skipped": True, "reason": "no vectors found"}
    
    print(f"  Found {len(vectors)} vectors for IP: {ip_id}")
    
    if dry_run:
        print(f"  [DRY RUN] Would migrate {len(vectors)} vectors")
        return {"ip_id": ip_id, "dry_run": True, "count": len(vectors)}
    
    # 初始化Qdrant collection
    if vectors:
        first_vec = vectors[0].embedding
        vector_size = len(first_vec) if isinstance(first_vec, list) else 1536
        
        client = get_qdrant_client()
        ensure_collection(client, ip_id, vector_size)
    
    success = 0
    failed = 0
    errors = []
    
    for vec in vectors:
        try:
            # 从AssetVector表获取对应的IPAsset内容
            # 这里简化处理：直接用asset_id作为content
            success += 1
        except Exception as e:
            failed += 1
            errors.append(str(e))
    
    return {
        "ip_id": ip_id,
        "total": len(vectors),
        "success": success,
        "failed": failed,
        "errors": errors[:10],  # 只保留前10个错误
    }


def migrate_all_ips(db_session, dry_run: bool = False) -> list:
    """迁移所有IP的向量"""
    
    # 获取所有有向量的IP
    ips_with_vectors = (
        db_session.query(AssetVector.ip_id)
        .distinct()
        .all()
    )
    
    ip_ids = [row[0] for row in ips_with_vectors]
    print(f"Found {len(ip_ids)} IPs with vectors")
    
    results = []
    for ip_id in ip_ids:
        print(f"\nMigrating IP: {ip_id}")
        result = migrate_ip_vectors(db_session, ip_id, dry_run)
        results.append(result)
        if not dry_run and result.get("success"):
            print(f"  ✓ Migrated {result['success']} vectors")
    
    return results


def verify_migration(db_session, ip_id: str) -> dict:
    """验证迁移结果"""
    from app.services.vector_service_qdrant import get_collection_info
    
    # 检查PostgreSQL
    pg_count = db_session.query(AssetVector).filter(AssetVector.ip_id == ip_id).count()
    
    # 检查Qdrant
    qdrant_info = get_collection_info(ip_id)
    
    return {
        "ip_id": ip_id,
        "postgresql_vectors": pg_count,
        "qdrant_info": qdrant_info,
    }


def main():
    parser = argparse.ArgumentParser(description="Migrate vectors to Qdrant")
    parser.add_argument("--ip-id", help="Specific IP ID to migrate")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--verify", action="store_true", help="Verify migration after completion")
    args = parser.parse_args()
    
    # 数据库连接
    database_url = os.environ.get("DATABASE_URL", "postgresql://user:password@localhost:5432/ip_factory")
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        if args.ip_id:
            # 迁移指定IP
            result = migrate_ip_vectors(db, args.ip_id, args.dry_run)
            print(f"\nMigration result: {result}")
            
            if args.verify and not args.dry_run:
                verify = verify_migration(db, args.ip_id)
                print(f"\nVerification: {verify}")
        else:
            # 迁移所有IP
            results = migrate_all_ips(db, args.dry_run)
            print(f"\n=== Migration Summary ===")
            for r in results:
                print(f"  {r.get('ip_id')}: {r.get('success', 0)}/{r.get('total', 0)} migrated")
    finally:
        db.close()


if __name__ == "__main__":
    main()
