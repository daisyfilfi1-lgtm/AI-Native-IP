# 选题推荐系统 V3.0 部署脚本 (PowerShell)
# 在 PowerShell 中运行: .\scripts\deploy_v3.ps1

Write-Host "🚀 开始部署选题推荐系统 V3.0..." -ForegroundColor Green

# 检查是否在项目根目录
if (-not (Test-Path "backend\app\services")) {
    Write-Host "❌ 错误: 请在项目根目录运行此脚本" -ForegroundColor Red
    exit 1
}

# 1. 备份现有代码
Write-Host "📦 步骤1: 备份现有代码..." -ForegroundColor Yellow
$backupDir = "backend\app\services.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item -Recurse "backend\app\services" $backupDir
Write-Host "✅ 备份完成: $backupDir" -ForegroundColor Green

# 2. 检查新文件
Write-Host "📋 步骤2: 检查部署文件..." -ForegroundColor Yellow
$requiredFiles = @(
    "backend\app\services\datasource\__init__.py",
    "backend\app\services\datasource\base.py",
    "backend\app\services\datasource\cache.py",
    "backend\app\services\datasource\builtin_source.py",
    "backend\app\services\datasource\free_sources.py",
    "backend\app\services\datasource\paid_sources.py",
    "backend\app\services\datasource\platform_sources.py",
    "backend\app\services\datasource\manager_v2.py",
    "backend\app\services\keyword_synonyms.py",
    "backend\app\services\enhanced_topic_matcher.py",
    "backend\app\services\topic_rewrite_service.py",
    "backend\app\services\topic_recommendation_v3.py"
)

$missingFiles = $requiredFiles | Where-Object { -not (Test-Path $_) }
if ($missingFiles) {
    Write-Host "❌ 错误: 缺少以下文件:" -ForegroundColor Red
    $missingFiles | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host "✅ 所有文件检查通过" -ForegroundColor Green

# 3. 注册路由
Write-Host "🔧 步骤3: 注册API路由..." -ForegroundColor Yellow
$mainFile = "backend\app\main.py"
$mainContent = Get-Content $mainFile -Raw

if ($mainContent -notmatch "topic_recommendation_v2") {
    $routeCode = @"

# V3.0 选题推荐路由
try:
    from app.routers import topic_recommendation_v2
    app.include_router(
        topic_recommendation_v2.router,
        prefix="/api/v1",
        tags=["topic-recommendation-v2"]
    )
    print("✅ V3.0 选题推荐路由已注册")
except ImportError as e:
    print(f"⚠️ V3.0 路由注册失败: {e}")
"@
    Add-Content -Path $mainFile -Value $routeCode
    Write-Host "✅ 路由注册完成" -ForegroundColor Green
} else {
    Write-Host "⚠️ 路由已注册，跳过" -ForegroundColor Yellow
}

# 4. 检查环境变量
Write-Host "🔧 步骤4: 检查环境变量..." -ForegroundColor Yellow
$hasApiKey = $env:SHUNWEI_API_KEY -or $env:QQLYKM_API_KEY -or $env:TIKHUB_API_KEY

if (-not $hasApiKey) {
    Write-Host "⚠️ 警告: 未配置任何付费API Key" -ForegroundColor Yellow
    Write-Host "系统将使用内置库（零成本，100%可用）"
    Write-Host ""
    Write-Host "如需配置付费源，请设置以下环境变量:" -ForegroundColor Cyan
    Write-Host '  $env:SHUNWEI_API_KEY="your_key"    # 顺为数据，10元/月'
    Write-Host '  $env:QQLYKM_API_KEY="your_key"     # QQ来客源，10元/3000次'
    Write-Host '  $env:TIKHUB_API_KEY="your_key"     # TIKHUB（如有）'
}

# 5. 验证Python语法
Write-Host "🔍 步骤5: 验证代码..." -ForegroundColor Yellow
$testCode = @"
from app.services.datasource import get_datasource_manager_v2
manager = get_datasource_manager_v2()
print(f'✅ 数据源管理器初始化成功')
print(f'   注册数据源: {len(manager.list_sources())} 个')
print(f'   可用数据源: {len(manager.list_available_sources())} 个')
"@

cd backend
$testCode | python 2>&1 | ForEach-Object {
    if ($_ -match "ERROR|Error") {
        Write-Host "❌ $_" -ForegroundColor Red
    } else {
        Write-Host $_
    }
}

cd ..

Write-Host ""
Write-Host "🎉 部署完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📖 下一步:" -ForegroundColor Cyan
Write-Host "  1. 启动服务: cd backend; python -m uvicorn app.main:app --reload"
Write-Host "  2. 测试API: 访问 http://localhost:8000/api/v1/strategy/v2/topics/builtin?ip_id=xiaomin1&limit=12"
Write-Host "  3. 查看文档: docs/上线部署指南.md"
Write-Host ""
Write-Host "⚠️  回滚命令（如需要）:" -ForegroundColor Yellow
Write-Host "  Remove-Item -Recurse backend\app\services\datasource"
Write-Host "  Copy-Item -Recurse $backupDir backend\app\services\datasource"
