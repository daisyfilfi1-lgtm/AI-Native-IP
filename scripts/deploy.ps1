# AI-Native IP 工厂前端 - Netlify 部署脚本 (PowerShell)

Write-Host "🚀 开始部署到 Netlify..." -ForegroundColor Cyan

# 检查 netlify-cli 是否安装
$netlifyCmd = Get-Command netlify -ErrorAction SilentlyContinue
if (-not $netlifyCmd) {
    Write-Host "📦 安装 Netlify CLI..." -ForegroundColor Yellow
    npm install -g netlify-cli
}

# 检查是否登录
$loginStatus = netlify status 2>&1
if ($loginStatus -match "Not logged in") {
    Write-Host "🔑 请登录 Netlify..." -ForegroundColor Yellow
    netlify login
}

# 安装依赖
Write-Host "📦 安装依赖..." -ForegroundColor Yellow
npm ci

# 构建
Write-Host "🔨 构建项目..." -ForegroundColor Yellow
npm run build

# 检查构建是否成功
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 构建失败！" -ForegroundColor Red
    exit 1
}

# 部署
Write-Host "🚀 部署到 Netlify..." -ForegroundColor Yellow
netlify deploy --build --prod

Write-Host "✅ 部署完成！" -ForegroundColor Green
