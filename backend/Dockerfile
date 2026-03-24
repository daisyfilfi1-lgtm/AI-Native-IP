# 供 Railway「Root Directory = backend」部署：构建上下文为 backend/，勿依赖仓库根目录。
# 与仓库根 Dockerfile 行为一致：迁移后启动 Uvicorn。
FROM python:3.11-slim

# 安装 SSL 证书（解决 HTTPS 拉取问题）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x worker_entrypoint.sh

ENV PORT=8000
EXPOSE $PORT
CMD sh -c "python scripts/run_migrations.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
