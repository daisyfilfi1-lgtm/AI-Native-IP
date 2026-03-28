# 供 Railway「Root Directory = backend」部署：构建上下文为 backend/，勿依赖仓库根目录。
# 与仓库根 Dockerfile 行为一致：迁移后启动 Uvicorn。
FROM python:3.11-slim

# 安装系统依赖（包括 Playwright 需要的依赖）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Chromium 及系统依赖（--with-deps 会 apt 装库并下载浏览器；勿只装 pip 包）
RUN python -m playwright install chromium --with-deps

COPY . .
RUN chmod +x worker_entrypoint.sh

# 不在镜像里写死 PORT：生产由 Railway 注入；本地未设置时 CMD 里回退 8000。
EXPOSE 8000
CMD sh -c "python scripts/run_migrations.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
