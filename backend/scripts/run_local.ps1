# 本地一键跑通脚本 (PowerShell)
# 用法: .\scripts\run_local.ps1
# 前置: 1) Docker 已安装并启动  2) 已配置 OPENAI_API_KEY 到 .env

$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $backend

Write-Host "=== 1. 启动 PostgreSQL ===" -ForegroundColor Cyan
docker-compose up -d postgres 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker 未运行或 docker-compose 失败，请先启动 Docker Desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== 2. 等待数据库就绪 ===" -ForegroundColor Cyan
Start-Sleep -Seconds 3

Write-Host "=== 3. 执行数据库迁移 ===" -ForegroundColor Cyan
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ip_factory"
python scripts/run_migrations.py

Write-Host "=== 4. 启动后端 (Ctrl+C 停止) ===" -ForegroundColor Cyan
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
