#!/usr/bin/env python3
"""Diagnose file upload and vector generation flow"""
import os
import sys

# Setup path and load env
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app.env_loader import load_backend_env
load_backend_env()

print("="*60)
print("1. STORAGE CONFIG CHECK")
print("="*60)
from app.config.storage_config import get_storage_config
storage_cfg = get_storage_config()
print(f"  S3 Enabled: {storage_cfg.get('s3_enabled')}")
print(f"  Local Enabled: {storage_cfg.get('local_enabled')}")
print(f"  Endpoint: {storage_cfg.get('endpoint')}")
print(f"  Bucket: {storage_cfg.get('bucket')}")

print("\n" + "="*60)
print("2. AI CONFIG CHECK")
print("="*60)
from app.config.ai_config import get_ai_config
ai_cfg = get_ai_config()
print(f"  API Key: {'Configured' if ai_cfg.get('api_key') else 'NOT configured'}")
print(f"  Base URL: {ai_cfg.get('base_url')}")
print(f"  Embedding Model: {ai_cfg.get('embedding_model')}")
print(f"  LLM Model: {ai_cfg.get('llm_model')}")
print(f"  Embedding Available: {ai_cfg.get('embedding_available')}")

print("\n" + "="*60)
print("3. TEST EMBEDDING")
print("="*60)
from app.services.ai_client import embed
test_texts = ["Hello, this is a test text"]
try:
    result = embed(test_texts)
    if result and result[0]:
        print(f"  OK! Embedding dimension: {len(result[0])}")
    else:
        print("  FAIL: Embedding returned empty")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n" + "="*60)
print("4. TEST OSS UPLOAD")
print("="*60)
from app.services.storage_service import upload_bytes
test_data = b"Hello, this is a test file content"
try:
    result = upload_bytes("test_ip", "test.txt", "text/plain", test_data)
    if result:
        print(f"  OK! Upload success!")
        print(f"      File ID: {result.get('file_id')}")
        print(f"      Bucket: {result.get('bucket')}")
        print(f"      Object Key: {result.get('object_key')}")
    else:
        print("  FAIL: Upload returned None")
except Exception as e:
    print(f"  FAIL: {e}")

print("\n" + "="*60)
print("5. DATABASE CHECK")
print("="*60)
from app.db.session import SessionLocal
from app.db.models import IP, FileObject, IngestTask, IPAsset, AssetVector
db = SessionLocal()
try:
    # Test connection
    db.execute("SELECT 1")
    print("  OK! Database connection works")
    
    # Counts
    ip_count = db.query(IP).count()
    file_count = db.query(FileObject).count()
    asset_count = db.query(IPAsset).count()
    vector_count = db.query(AssetVector).count()
    
    print(f"  IPs: {ip_count}")
    print(f"  Files: {file_count}")
    print(f"  Assets: {asset_count}")
    print(f"  Vectors: {vector_count}")
except Exception as e:
    print(f"  FAIL: {e}")
finally:
    db.close()

print("\n" + "="*60)
print("6. QDRANT CONFIG")
print("="*60)
qdrant_url = os.environ.get("QDRANT_URL", "")
qdrant_key = os.environ.get("QDRANT_API_KEY", "")
print(f"  URL: {qdrant_url[:30]}..." if qdrant_url else "  URL: NOT configured")
print(f"  API Key: {'Configured' if qdrant_key else 'NOT configured'}")

if qdrant_url and qdrant_key:
    try:
        from app.services.vector_service_qdrant import get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections()
        print(f"  OK! Qdrant works, collections: {len(collections.collections)}")
    except Exception as e:
        print(f"  FAIL: {e}")

print("\n" + "="*60)
print("DIAGNOSIS COMPLETE")
print("="*60)
