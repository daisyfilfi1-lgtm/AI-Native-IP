"""
队列模块 - 处理后台任务入队

支持两种模式：
1. RQ队列（需要REDIS_URL配置）：任务入Redis队列，由worker处理
2. Fallback：直接用BackgroundTasks（同步执行）

Railway生产环境建议：配置REDIS_URL使用RQ
"""
import os
import logging

logger = logging.getLogger(__name__)


def _is_queue_enabled() -> bool:
    """检查是否启用RQ队列"""
    redis_url = os.environ.get("REDIS_URL", "").strip()
    return bool(redis_url)


def enqueue_ingest(task_id: str) -> bool:
    """
    将ingest任务加入队列
    
    Returns:
        True: 成功加入队列（由worker处理）
        False: 队列不可用（将使用BackgroundTasks）
    """
    if not _is_queue_enabled():
        logger.info(f"[Queue] REDIS_URL未配置，任务 {task_id} 将使用BackgroundTasks执行")
        return False
    
    try:
        from rq import Queue
        from redis import Redis
        from app.services.ai_client import get_redis_connection
        
        # 获取Redis连接
        redis_url = os.environ.get("REDIS_URL")
        
        # 尝试直接连接
        try:
            conn = Redis.from_url(redis_url)
            conn.ping()
        except Exception as e:
            logger.warning(f"[Queue] Redis连接失败: {e}，回退到BackgroundTasks")
            return False
        
        q = Queue("ingest", connection=conn)
        
        # 入队（延迟执行，让调用方先返回响应）
        q.enqueue(
            "app.services.ingest_service.process_ingest_task",
            task_id,
            job_timeout=300,  # 5分钟超时
            result_ttl=86400,  # 结果保留1天
        )
        
        logger.info(f"[Queue] 任务 {task_id} 已入队 (RQ)")
        return True
        
    except ImportError:
        logger.warning("[Queue] rq未安装，回退到BackgroundTasks")
        return False
    except Exception as e:
        logger.warning(f"[Queue] 入队失败: {e}，回退到BackgroundTasks")
        return False


def get_queue_stats() -> dict:
    """获取队列状态（用于监控）"""
    if not _is_queue_enabled():
        return {"enabled": False, "mode": "background_tasks"}
    
    try:
        from rq import Queue
        from redis import Redis
        
        redis_url = os.environ.get("REDIS_URL")
        conn = Redis.from_url(redis_url)
        q = Queue("ingest", connection=conn)
        
        return {
            "enabled": True,
            "mode": "rq",
            "queued_jobs": len(q),
            "failed_jobs": q.failed_job_registry.count,
            "worker_count": len(q.workers),
        }
    except Exception as e:
        return {"enabled": False, "error": str(e)}
