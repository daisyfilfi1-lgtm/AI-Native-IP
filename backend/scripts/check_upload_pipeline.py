#!/usr/bin/env python3
"""
素材上传链路连通性检查脚本
用法: cd backend && python scripts/check_upload_pipeline.py
"""
import os
import sys

# 确保能加载 backend 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.env_loader import load_backend_env

load_backend_env()


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "✓" if ok else "✗"
    print(f"  [{status}] {name}" + (f" - {detail}" if detail else ""))


def main() -> None:
    print("=== IP 素材上传链路检查 ===\n")

    # 1. 数据库
    print("1. 数据库 (PostgreSQL)")
    db_url = os.environ.get("DATABASE_URL", "")
    db_ok = bool(db_url and "postgresql" in db_url)
    check("DATABASE_URL 已配置", db_ok, "未配置" if not db_ok else f"已配置 ({db_url.split('@')[-1] if '@' in db_url else '...'})")

    if db_ok:
        try:
            from sqlalchemy import text
            from app.db.session import SessionLocal
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            check("数据库连接成功", True)
        except Exception as e:
            check("数据库连接", False, str(e)[:80])
    print()

    # 2. 对象存储
    print("2. 对象存储 (S3/OSS) - 本地上传需要")
    cfg_keys = ["STORAGE_ENDPOINT", "STORAGE_ACCESS_KEY", "STORAGE_SECRET_KEY", "STORAGE_BUCKET"]
    storage_vals = [os.environ.get(k, "").strip() for k in cfg_keys]
    storage_ok = all(storage_vals)
    check("STORAGE_* 已配置", storage_ok, "未配置时 /memory/upload 不可用" if not storage_ok else "可支持本地上传")
    print()

    # 3. Embedding
    print("3. Embedding (向量化)")
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip()
    embed_ok = bool(api_key)
    check("OPENAI_API_KEY 已配置", embed_ok, "未配置时向量写入会跳过，检索回退关键词" if not embed_ok else "支持语义检索")
    if embed_ok and base_url:
        check("OPENAI_BASE_URL", True, base_url[:50] + "..." if len(base_url) > 50 else base_url)
    print()

    # 4. 转写
    print("4. 语音转写 (Whisper) - audio/video 需要")
    trans_key = os.environ.get("OPENAI_TRANSCRIPTION_API_KEY", "").strip() or api_key
    trans_ok = bool(trans_key)
    check("转写 API Key 已配置", trans_ok, "未配置时音视频会写入占位提示" if not trans_ok else "可转写音视频")
    print()

    # 5. Qdrant
    print("5. Qdrant 向量库 (可选)")
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=qdrant_url, timeout=3)
        client.get_collections()
        check("Qdrant 连接成功", True, qdrant_url)
    except Exception as e:
        check("Qdrant", False, f"未连接 ({str(e)[:50]})；/vector/search 会回退 PostgreSQL")
    print()

    # 6. 表结构
    print("6. 数据库表")
    if db_ok:
        try:
            from sqlalchemy import inspect
            from app.db.session import engine
            insp = inspect(engine)
            tables = ["ip", "ip_assets", "ingest_tasks", "file_objects", "asset_vectors"]
            for t in tables:
                has = t in insp.get_table_names()
                check(f"表 {t}", has, "" if has else "缺失，需执行迁移")
        except Exception as e:
            check("表检查", False, str(e)[:60])
    print()

    print("=== 检查完成 ===")
    print("\n推荐测试：")
    print("  URL 录入: POST /api/v1/memory/ingest (source_url)")
    print("  本地上传: POST /api/v1/memory/upload -> ingest (local_file_id)")
    print("  验证:     GET /api/v1/memory/assets?ip_id=xxx")


if __name__ == "__main__":
    main()
