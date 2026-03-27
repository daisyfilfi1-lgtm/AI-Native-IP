# 从 backend 目录构建并运行，便于在仓库根目录被平台识别
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
RUN chmod +x worker_entrypoint.sh

# 不在镜像里写死 PORT：生产由 Railway 注入；本地未设置时 CMD 里回退 8000。
EXPOSE 8000
# 启动前自动执行数据库迁移（CREATE TABLE IF NOT EXISTS，可重复执行）
CMD sh -c "python scripts/run_migrations.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
