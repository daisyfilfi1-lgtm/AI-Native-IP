"""
Redis Queue 配置，用于后台任务（录入等）。
需配置 REDIS_URL 环境变量；未配置时返回 None，调用方需回退到同步或跳过。
"""
import os

_redis_url: str | None = None
_queue = None


def get_redis_url() -> str | None:
    global _redis_url
    if _redis_url is None:
        u = os.getenv("REDIS_URL", "").strip()
        _redis_url = u if u else None
    return _redis_url


def get_queue():
    """获取 RQ default 队列；Redis 未配置时返回 None。"""
    global _queue
    if _queue is not None:
        return _queue
    url = get_redis_url()
    if not url:
        return None
    try:
        from redis import Redis
        from rq import Queue
        conn = Redis.from_url(url)
        _queue = Queue(connection=conn, default_timeout=300)
        return _queue
    except Exception:
        return None


def enqueue_ingest(task_id: str) -> bool:
    """将录入任务加入 RQ；成功返回 True，失败返回 False。"""
    q = get_queue()
    if not q:
        return False
    try:
        from app.services.ingest_service import process_ingest_task
        q.enqueue(process_ingest_task, task_id, job_timeout=300)
        return True
    except Exception:
        return False
