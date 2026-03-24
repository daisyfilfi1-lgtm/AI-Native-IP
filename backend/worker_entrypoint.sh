#!/bin/bash
set -e

cd /app
export PYTHONPATH=/app:$PYTHONPATH

# 加载环境变量
python -c "from app.env_loader import load_backend_env; load_backend_env()"

# 检查 REDIS_URL
if [ -z "$REDIS_URL" ]; then
    echo "ERROR: REDIS_URL not set"
    exit 1
fi

# 运行 RQ Worker
exec python scripts/worker.py
