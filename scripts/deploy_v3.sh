#!/bin/bash
# 选题推荐系统 V3.0 部署脚本

set -e  # 遇到错误立即退出

echo "🚀 开始部署选题推荐系统 V3.0..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在项目根目录
if [ ! -d "backend/app/services" ]; then
    echo -e "${RED}❌ 错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 1. 备份现有代码
echo "📦 步骤1: 备份现有代码..."
BACKUP_DIR="backend/app/services.backup.$(date +%Y%m%d_%H%M%S)"
cp -r backend/app/services "$BACKUP_DIR"
echo -e "${GREEN}✅ 备份完成: $BACKUP_DIR${NC}"

# 2. 检查新文件是否存在
echo "📋 步骤2: 检查部署文件..."
REQUIRED_FILES=(
    "backend/app/services/datasource/__init__.py"
    "backend/app/services/datasource/base.py"
    "backend/app/services/datasource/cache.py"
    "backend/app/services/datasource/builtin_source.py"
    "backend/app/services/datasource/free_sources.py"
    "backend/app/services/datasource/paid_sources.py"
    "backend/app/services/datasource/platform_sources.py"
    "backend/app/services/datasource/manager_v2.py"
    "backend/app/services/keyword_synonyms.py"
    "backend/app/services/enhanced_topic_matcher.py"
    "backend/app/services/topic_rewrite_service.py"
    "backend/app/services/topic_recommendation_v3.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ 错误: 缺少文件 $file${NC}"
        echo "请确保所有新代码文件已准备就绪"
        exit 1
    fi
done
echo -e "${GREEN}✅ 所有文件检查通过${NC}"

# 3. 安装依赖（如果需要）
echo "📦 步骤3: 检查依赖..."
if ! python -c "import httpx" 2>/dev/null; then
    echo "安装 httpx..."
    pip install httpx -q
fi
echo -e "${GREEN}✅ 依赖检查完成${NC}"

# 4. 注册路由（自动修改main.py）
echo "🔧 步骤4: 注册API路由..."
MAIN_FILE="backend/app/main.py"

if ! grep -q "topic_recommendation_v2" "$MAIN_FILE"; then
    # 在文件末尾添加路由注册
    cat >> "$MAIN_FILE" << 'EOF'

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
EOF
    echo -e "${GREEN}✅ 路由注册完成${NC}"
else
    echo -e "${YELLOW}⚠️ 路由已注册，跳过${NC}"
fi

# 5. 检查环境变量
echo "🔧 步骤5: 检查环境变量..."
if [ -z "$SHUNWEI_API_KEY" ] && [ -z "$QQLYKM_API_KEY" ] && [ -z "$TIKHUB_API_KEY" ]; then
    echo -e "${YELLOW}⚠️ 警告: 未配置任何付费API Key${NC}"
    echo "系统将使用内置库和免费API（如果有）"
    echo ""
    echo "如需配置付费源，请设置以下环境变量："
    echo "  export SHUNWEI_API_KEY=your_key    # 顺为数据，10元/月"
    echo "  export QQLYKM_API_KEY=your_key     # QQ来客源，10元/3000次"
    echo "  export TIKHUB_API_KEY=your_key     # TIKHUB（如有）"
    echo ""
    echo "或使用内置库（零成本，100%可用）："
    echo "  无需配置，直接启动即可"
fi

# 6. 验证Python语法
echo "🔍 步骤6: 验证代码..."
python -m py_compile backend/app/services/datasource/__init__.py
python -m py_compile backend/app/services/topic_recommendation_v3.py
python -m py_compile backend/app/services/topic_rewrite_service.py
echo -e "${GREEN}✅ 代码验证通过${NC}"

# 7. 尝试启动服务验证
echo "🚀 步骤7: 验证服务启动..."
cd backend
python -c "
from app.services.datasource import get_datasource_manager_v2
manager = get_datasource_manager_v2()
print(f'✅ 数据源管理器初始化成功')
print(f'   注册数据源: {len(manager.list_sources())} 个')
print(f'   可用数据源: {len(manager.list_available_sources())} 个')
" || {
    echo -e "${RED}❌ 服务初始化失败，请检查错误日志${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}🎉 部署完成！${NC}"
echo ""
echo "📖 下一步："
echo "  1. 启动服务: cd backend && python -m uvicorn app.main:app --reload"
echo "  2. 测试API: curl http://localhost:8000/api/v1/strategy/v2/topics/builtin?ip_id=xiaomin1&limit=12"
echo "  3. 查看文档: docs/上线部署指南.md"
echo ""
echo "⚠️  回滚命令（如需要）:"
echo "  rm -rf backend/app/services/datasource"
echo "  cp -r $BACKUP_DIR backend/app/services/datasource"
