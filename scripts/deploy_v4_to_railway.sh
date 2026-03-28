#!/bin/bash
# ============================================================
# V4选题推荐系统 - Railway一键部署脚本
# 在Railway容器的Shell中执行此脚本
# ============================================================

set -e  # 遇到错误立即退出

echo "🚀 开始部署V4选题推荐系统..."
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================
# 1. 检查环境
# ============================================================
echo -e "${YELLOW}Step 1: 检查环境...${NC}"

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ 错误: DATABASE_URL 环境变量未设置${NC}"
    exit 1
fi

echo "✅ DATABASE_URL 已配置"
echo ""

# ============================================================
# 2. 更新代码
# ============================================================
echo -e "${YELLOW}Step 2: 拉取最新代码...${NC}"

cd /app 2>/dev/null || cd $(pwd)

git pull origin master
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 代码拉取失败${NC}"
    exit 1
fi

echo "✅ 代码已更新到最新版本"
echo ""

# ============================================================
# 3. 创建数据库表
# ============================================================
echo -e "${YELLOW}Step 3: 创建数据库表...${NC}"

psql $DATABASE_URL -f backend/scripts/create_competitor_tables.sql
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 创建表失败${NC}"
    exit 1
fi

echo "✅ 数据库表创建完成"
echo ""

# ============================================================
# 4. 插入竞品账号
# ============================================================
echo -e "${YELLOW}Step 4: 配置17个竞品账号...${NC}"

psql $DATABASE_URL -f backend/scripts/setup_competitors_from_analysis.sql
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 插入竞品账号失败${NC}"
    exit 1
fi

echo "✅ 17个竞品账号已配置"
echo ""

# ============================================================
# 5. 插入示例视频数据
# ============================================================
echo -e "${YELLOW}Step 5: 插入示例爆款视频数据...${NC}"

psql $DATABASE_URL -f backend/scripts/seed_competitor_videos.sql
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 插入视频数据失败${NC}"
    exit 1
fi

echo "✅ 示例视频数据已插入"
echo ""

# ============================================================
# 6. 验证数据
# ============================================================
echo -e "${YELLOW}Step 6: 验证数据...${NC}"

echo "  检查竞品账号数量:"
psql $DATABASE_URL -c "SELECT 'Competitor Accounts' as item, COUNT(*) as count FROM competitor_accounts WHERE ip_id = 'xiaomin';"

echo ""
echo "  检查视频数量:"
psql $DATABASE_URL -c "SELECT 'Competitor Videos' as item, COUNT(*) as count FROM competitor_videos cv JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id WHERE ca.ip_id = 'xiaomin';"

echo ""
echo "  TOP 3 爆款视频:"
psql $DATABASE_URL -c "
SELECT 
    ca.name as competitor,
    LEFT(cv.title, 40) as title,
    cv.play_count,
    cv.content_type
FROM competitor_videos cv
JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
WHERE ca.ip_id = 'xiaomin'
ORDER BY cv.play_count DESC
LIMIT 3;
"

echo ""

# ============================================================
# 7. 测试API
# ============================================================
echo -e "${YELLOW}Step 7: 测试API...${NC}"

# 等待服务就绪
sleep 2

# 测试API (本地测试)
echo "  测试 /content/topics/recommend API..."
curl -s -X POST http://localhost:8000/api/v1/content/topics/recommend \
  -H "Content-Type: application/json" \
  -d '{"ip_id": "xiaomin", "count": 3}' | python3 -m json.tool > /tmp/api_test.json 2>/dev/null || true

if [ -f /tmp/api_test.json ] && [ -s /tmp/api_test.json ]; then
    echo "  API响应预览:"
    cat /tmp/api_test.json | head -50
    
    # 检查是否包含V4数据
    if grep -q "_v4_data" /tmp/api_test.json; then
        echo ""
        echo -e "${GREEN}✅ API响应中包含V4数据！${NC}"
    else
        echo ""
        echo -e "${YELLOW}⚠️ API响应中未包含V4数据（可能是LLM生成模式）${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ API测试失败，请手动测试${NC}"
fi

echo ""

# ============================================================
# 8. 完成
# ============================================================
echo -e "${GREEN}🎉 V4选题推荐系统部署完成！${NC}"
echo ""
echo "📊 部署摘要:"
echo "  - 17个竞品账号已配置"
echo "  - 20+示例爆款视频已导入"
echo "  - API已更新，优先使用竞品数据"
echo ""
echo "🔗 测试链接:"
echo "  curl -X POST http://localhost:8000/api/v1/content/topics/recommend \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"ip_id\": \"xiaomin\", \"count\": 6}'"
echo ""
echo "💡 提示: 如需抓取真实竞品数据，请配置 TIKHUB_API_KEY 环境变量"
