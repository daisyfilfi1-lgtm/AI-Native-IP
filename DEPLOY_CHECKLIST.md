# 仿写流程修复 - 前后端部署清单

## 📦 后端部署

### 新增文件
```
backend/app/services/link_resolver.py              # 链接解析器（新）
backend/app/services/text_extractor.py             # 统一文本提取服务（新）
backend/docs/TEXT_EXTRACTION_ARCHITECTURE.md       # 架构文档
backend/docs/REMIX_FIX_REPORT.md                   # 修复报告
backend/docs/ARCHITECTURE_COMPARISON.md            # 架构对比
backend/docs/COPYWRITING_EXTRACTOR_ANALYSIS.md     # 第三方工具分析
backend/docs/INTEGRATION_SUMMARY.md                # 集成总结
backend/test_text_extraction.py                    # 测试脚本
backend/test_remix_fix.md                          # 验证文档
backend/test_remix_flow_fixed.py                   # 流程图
```

### 修改文件
```
backend/app/services/competitor_text_extraction.py # 简化，调用新服务
backend/app/routers/creator.py                     # 支持手动输入模式
backend/app/services/content_scenario.py           # 输入校验增强
```

### 部署步骤

```bash
# 1. 进入后端目录
cd backend

# 2. 安装依赖（如需要）
pip install httpx

# 3. 可选：安装 yt-dlp
pip install yt-dlp

# 4. 环境变量配置（如使用 TikHub）
export TIKHUB_API_KEY="your_api_key"
export TIKHUB_BASE_URL="https://api.tikhub.io"

# 5. 可选：启用 yt-dlp
export REMIX_YTDLP_FALLBACK="1"

# 6. 重启服务
# 根据部署方式选择：
# - Docker: docker-compose restart
# - PM2: pm2 restart app
# - Systemd: systemctl restart ip-factory
# - 直接: python -m uvicorn app.main:app --reload
```

---

## 🎨 前端部署

### 新增文件
```
frontend/components/creator/ThirdPartyExtractor.tsx  # 第三方工具组件
```

### 修改文件
```
frontend/app/creator/dashboard/page.tsx    # 集成第三方工具UI
frontend/lib/api/creator.ts                # 错误处理增强
```

### 部署步骤

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖（如有新依赖）
npm install
# 或
yarn install

# 3. 构建
npm run build
# 或
yarn build

# 4. 部署
# - Vercel: vercel --prod
# - Netlify: netlify deploy --prod
# - 静态托管: 复制 dist/out 到服务器
```

---

## 🔧 关键配置检查

### 后端环境变量
```bash
# 必需
export DATABASE_URL="postgresql://..."

# 仿写功能相关
export TIKHUB_API_KEY=""           # 可选，但推荐配置
export REMIX_YTDLP_FALLBACK="0"    # 可选，安装 yt-dlp 后设为 "1"
export REMIX_V2_ENABLED="true"     # 启用新版仿写流程
```

### 前端环境变量
```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL="https://your-api.com"
NEXT_PUBLIC_API_KEY="your-api-key"
```

---

## ✅ 部署验证清单

### 后端验证
- [ ] 服务启动无报错
- [ ] API 接口可访问
- [ ] 测试链接解析：
  ```bash
  curl -X POST /api/v1/creator/generate/remix \
    -H "Content-Type: application/json" \
    -d '{"url":"https://v.douyin.com/xxxxx","style":"angry","ipId":"xiaomin1"}'
  ```

### 前端验证
- [ ] 页面正常加载
- [ ] 仿写Tab可点击
- [ ] 输入链接后显示推荐工具
- [ ] 手动输入模式可用

### 端到端验证
- [ ] 有效链接 → 自动提取 → 仿写成功
- [ ] 无效链接 → 显示错误 → 显示第三方工具
- [ ] 点击第三方工具 → 新标签页打开
- [ ] 手动粘贴 → 仿写成功

---

## 🚨 回滚方案

如遇到问题，可快速回滚：

```bash
# 后端回滚
git checkout HEAD~1 -- backend/app/services/competitor_text_extraction.py
git checkout HEAD~1 -- backend/app/routers/creator.py

# 前端回滚
git checkout HEAD~1 -- frontend/app/creator/dashboard/page.tsx
git checkout HEAD~1 -- frontend/lib/api/creator.ts

# 删除新增文件
rm backend/app/services/link_resolver.py
rm backend/app/services/text_extractor.py
rm frontend/components/creator/ThirdPartyExtractor.tsx
```

---

## 📊 部署后监控

### 关键指标
- 仿写请求成功率
- 各提取策略使用比例
- 第三方工具点击率
- 手动输入使用率

### 日志检查
```bash
# 查看提取相关日志
grep "extract\|remix\|tikhub\|web_scrape" /var/log/app.log

# 查看错误日志
grep "ERROR\|failed\|exception" /var/log/app.log
```

---

## 🆘 常见问题

### Q1: 第三方工具链接打不开？
A: 检查浏览器是否阻止弹窗，或工具网站是否可用。

### Q2: yt-dlp 未生效？
A: 确认已安装：`which yt-dlp`，并设置环境变量 `REMIX_YTDLP_FALLBACK=1`。

### Q3: TikHub 返回 403？
A: 检查 API Key 是否有效，权限是否开启。

### Q4: Web 爬取被拦截？
A: 正常现象，会 fallback 到下一策略或显示第三方工具。

---

## 📞 部署支持

如遇问题，检查：
1. 环境变量是否正确设置
2. 依赖是否安装完整
3. 日志中的具体错误信息
4. 网络连接是否正常（特别是 TikHub/yt-dlp）
