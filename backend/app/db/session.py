import os
from typing import Generator

from sqlalchemy import create_engine, pool
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.env_loader import load_backend_env

load_backend_env()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ip_factory",
)
# 云平台常提供 postgres://，SQLAlchemy 需 postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ─────────────────────────────────────────────
# Railway 环境检测与连接池优化
# ─────────────────────────────────────────────
is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None
is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"

if is_railway:
    # Railway 环境：保守连接池配置，防止资源耗尽
    # Pro Plan 默认 2GB RAM，连接数不宜过多
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "connect_timeout": 10,      # 连接超时10秒
            "options": "-c statement_timeout=30000",  # 查询超时30秒
        },
        poolclass=pool.QueuePool,
        pool_size=3,                    # 从5降到3，减少常驻连接
        max_overflow=5,                 # 从10降到5，限制峰值连接
        pool_timeout=10,                # 获取连接等待超时
        pool_recycle=300,               # 5分钟回收连接，防止失效
        pool_pre_ping=True,             # 连接前ping检测
        echo=False,                     # 关闭SQL日志，减少IO
    )
else:
    # 本地开发环境：宽松配置
    _connect_args = {}
    if "postgresql" in DATABASE_URL:
        _connect_args["connect_timeout"] = 10
    
    engine = create_engine(
        DATABASE_URL,
        connect_args=_connect_args,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：获取数据库会话，请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_with_timeout(timeout_ms: int = 30000) -> Generator[Session, None, None]:
    """
    带超时控制的数据库会话
    用于可能长时间运行的后台任务
    """
    db = SessionLocal()
    # 设置会话级别的超时
    if is_railway:
        db.execute(f"SET statement_timeout = {timeout_ms}")
    try:
        yield db
    finally:
        db.close()
