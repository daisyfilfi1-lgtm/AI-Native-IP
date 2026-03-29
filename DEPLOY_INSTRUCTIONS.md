# 后端部署说明

## 代码已推送

✅ GitHub: https://github.com/daisyfilfi1-lgtm/AI-Native-IP/commit/51c7472

## 部署方式

### 方式1：Railway自动部署（推荐）

Railway已配置自动部署，代码推送到master分支后会自动触发：

```bash
# 检查部署状态
curl https://timeless-production-xxxx.up.railway.app/health
```

### 方式2：手动部署

如果自动部署未触发，在Railway Dashboard手动部署：

1. 打开 https://railway.app/dashboard
2. 选择项目
3. 点击 "Redeploy"

### 方式3：CLI部署

```bash
# 登录Railway
railway login

# 部署
cd backend
railway up
```

## 新API端点

部署完成后，以下API可用：

### 环节1：竞品发现
```
GET /strategy/v4/competitor-videos?ip_id=xiaomin&limit=10
```

### 环节2：内容提取
```
POST /strategy/v4/extract-content
Body: {"url": "https://douyin.com/video/xxx"}
```

### 环节3：标题改写
```
POST /strategy/v3/title-rewrite
Body: {
  "ip_id": "xiaomin",
  "original_title": "...",
  "original_hook": "...",
  "original_body": "..."
}
```

### 环节4：内容生成
```
POST /strategy/v4/content-generate
Body: {
  "ip_id": "xiaomin",
  "title": "...",
  "hook": "...",
  "body": "..."
}
```

### 完整流程（一键）
```
POST /strategy/v4/complete-pipeline?ip_id=xiaomin&url=https://...
```

## 验证部署

```bash
# 健康检查
curl https://your-api-domain/health

# 测试API
curl "https://your-api-domain/strategy/v4/competitor-videos?ip_id=xiaomin&limit=1"
```
