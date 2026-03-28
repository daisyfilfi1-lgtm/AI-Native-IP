# 代码推送命令

## Git 提交和推送

### 1. 查看修改的文件
```bash
git status
```

### 2. 添加修改的文件

#### 后端文件
```bash
# 新增文件
git add backend/app/services/link_resolver.py
git add backend/app/services/text_extractor.py
git add backend/components/creator/ThirdPartyExtractor.tsx

# 修改文件
git add backend/app/services/competitor_text_extraction.py
git add backend/app/routers/creator.py
git add backend/app/services/content_scenario.py

# 文档和测试
git add backend/docs/
git add backend/test_*.py
```

#### 前端文件
```bash
# 新增文件
git add frontend/components/creator/ThirdPartyExtractor.tsx

# 修改文件
git add frontend/app/creator/dashboard/page.tsx
git add frontend/lib/api/creator.ts
```

#### 部署文档
```bash
git add DEPLOY_CHECKLIST.md
git add PUSH_COMMANDS.md
```

### 3. 提交代码

```bash
# 统一提交（推荐）
git commit -m "feat: 增强仿写流程文本提取能力

- 新增多平台链接解析器（抖音/小红书/快手/B站）
- 新增统一文本提取服务（TikHub + Web爬取 + yt-dlp）
- 支持手动输入模式作为后备方案
- 集成第三方文案提取工具（anytocopy等）
- 优化错误处理和用户提示
- 添加完整的架构文档和测试"

# 或分模块提交
# 后端
git add backend/
git commit -m "feat(backend): 重构文本提取服务，支持多策略提取"

# 前端
git add frontend/
git commit -m "feat(frontend): 添加第三方工具提取器和手动输入模式"

# 文档
git add *.md backend/docs/
git commit -m "docs: 添加架构文档和部署指南"
```

### 4. 推送到远程

```bash
# 推送到当前分支
git push origin $(git branch --show-current)

# 或指定分支
git push origin main
# 或
git push origin master
# 或
git push origin develop
```

### 5. 创建 Pull Request（如使用 PR 工作流）

```bash
# 推送后，在 GitHub/GitLab 上创建 PR
# 标题: feat: 增强仿写流程文本提取能力
# 描述: 见提交信息
```

---

## Docker 部署推送

### 构建并推送镜像

```bash
# 1. 构建后端镜像
cd backend
docker build -t your-registry/ip-factory-backend:remix-fix .

# 2. 推送镜像
docker push your-registry/ip-factory-backend:remix-fix

# 3. 构建前端镜像
cd ../frontend
docker build -t your-registry/ip-factory-frontend:remix-fix .

# 4. 推送镜像
docker push your-registry/ip-factory-frontend:remix-fix
```

### 使用 Docker Compose 部署

```bash
# 1. 更新镜像标签
sed -i 's/image: ip-factory-backend:.*/image: ip-factory-backend:remix-fix/' docker-compose.yml

# 2. 拉取新镜像
docker-compose pull

# 3. 重启服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f backend
```

---

## 快速部署脚本

### 后端一键部署
```bash
#!/bin/bash
# deploy_backend.sh

echo "🚀 部署后端服务..."

cd backend

# 拉取最新代码
git pull origin main

# 安装依赖
pip install -r requirements.txt

# 可选：安装 yt-dlp
pip install yt-dlp

# 重启服务
# 方式1: PM2
pm2 restart ip-factory-backend

# 方式2: Systemd
# systemctl restart ip-factory

# 方式3: Docker
# docker-compose restart backend

echo "✅ 后端部署完成"
```

### 前端一键部署
```bash
#!/bin/bash
# deploy_frontend.sh

echo "🚀 部署前端服务..."

cd frontend

# 拉取最新代码
git pull origin main

# 安装依赖
npm install

# 构建
npm run build

# 部署
# 方式1: Vercel
vercel --prod

# 方式2: 静态文件
# cp -r out/* /var/www/html/

# 方式3: Docker
docker build -t ip-factory-frontend:latest .
docker-compose up -d frontend

echo "✅ 前端部署完成"
```

---

## 环境变量配置

### 生产环境配置

```bash
# 在服务器上编辑环境变量
sudo vim /etc/environment
# 或
sudo vim ~/.bashrc

# 添加以下内容
export TIKHUB_API_KEY="your-production-api-key"
export TIKHUB_BASE_URL="https://api.tikhub.io"
export REMIX_YTDLP_FALLBACK="1"
export REMIX_V2_ENABLED="true"

# 使配置生效
source /etc/environment
# 或
source ~/.bashrc
```

---

## 验证部署

```bash
# 1. 检查服务状态
curl https://your-api.com/health

# 2. 测试仿写接口
curl -X POST https://your-api.com/api/v1/creator/generate/remix \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "url": "https://v.douyin.com/xxxxx",
    "style": "angry",
    "ipId": "xiaomin1"
  }'

# 3. 检查日志
tail -f /var/log/ip-factory/app.log
```

---

## 回滚命令

```bash
# 1. 查看提交历史
git log --oneline -10

# 2. 回滚到上一个版本
git reset --hard HEAD~1
git push origin main --force

# 3. 或回滚到指定版本
git reset --hard abc1234
git push origin main --force

# 4. 仅回滚特定文件
git checkout HEAD~1 -- backend/app/services/competitor_text_extraction.py
git commit -m "revert: 回滚文本提取服务"
git push origin main
```

---

## 总结

### 推送步骤
1. `git add` - 添加文件
2. `git commit` - 提交更改
3. `git push` - 推送到远程
4. 部署到服务器

### 关键文件（确保都添加）
- ✅ 后端：link_resolver.py, text_extractor.py
- ✅ 前端：ThirdPartyExtractor.tsx, dashboard/page.tsx
- ✅ 配置：环境变量更新
- ✅ 文档：DEPLOY_CHECKLIST.md
