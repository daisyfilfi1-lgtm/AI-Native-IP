"""
RQ Worker 入口。需配置 REDIS_URL。
用法：python scripts/worker.py
或：rq worker -u $REDIS_URL
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
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        print("ERROR: REDIS_URL not set")
        sys.exit(1)
    from rq import Worker
    from redis import Redis
    from rq import Queue
    conn = Redis.from_url(url)
    worker = Worker([Queue(connection=conn)], connection=conn)
    worker.work(with_scheduler=False)
