"""
手动迁移 API - 用于 Railway Console 执行迁移
用法: curl -X POST http://<railway-url>/api/admin/run-migration -H "X-API-Key: <key>"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.env_loader import load_backend_env

load_backend_env()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

import psycopg2
from fastapi import APIRouter

router = APIRouter()

MIGRATIONS = {
    "014": "db/migrations/014_competitor_system.sql",
    "015": "db/migrations/015_competitor_four_dim.sql",
}


@router.post("/admin/run-migration")
async def run_migration(migration_id: str):
    """执行指定迁移"""
    if migration_id not in MIGRATIONS:
        return {"error": f"Unknown migration: {migration_id}. Available: {list(MIGRATIONS.keys())}"}
    
    path = MIGRATIONS[migration_id]
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        # 执行 SQL（按分号分割）
        for stmt in content.split(";"):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                cur.execute(stmt)
        
        return {"status": "success", "migration": migration_id}
    except Exception as e:
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()