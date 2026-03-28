"""
将长期 PROCESSING 且无心跳的任务标记为 TIMEOUT。
可由 Render Cron 每 5 分钟调用：python scripts/run_stale_task_cleanup.py
"""
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.env_loader import load_backend_env

load_backend_env()

if __name__ == "__main__":
    from app.db.session import SessionLocal
    from app.services.ingest_service import mark_stale_processing_as_timeout

    stale_seconds = 300
    raw = os.environ.get("STALE_TASK_THRESHOLD_SECONDS", "").strip()
    if raw:
        try:
            stale_seconds = max(60, int(raw))
        except ValueError:
            pass

    db = SessionLocal()
    try:
        n = mark_stale_processing_as_timeout(db, stale_seconds=stale_seconds)
        print(f"Marked {n} stale PROCESSING task(s) as TIMEOUT (threshold={stale_seconds}s)")
    finally:
        db.close()
