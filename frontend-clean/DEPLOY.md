# AI-Native IP 工厂前端部署指南

## 部署选项

### 方案一：部署到 Vercel（推荐）

Vercel 是 Next.js 的官方托管平台，提供最佳的性能和体验。

#### 步骤：

1. **准备代码**
```bash
cd frontend
git init
git add .
git commit -m "Initial commit"
```

2. **安装 Vercel CLI**
```bash
npm i -g vercel
```

3. **登录 Vercel**
```bash
vercel login
```

4. **部署**
```bash
# 首次部署
vercel

# 生产部署
vercel --prod
```

5. **环境变量**：生产环境**不要**把 `NEXT_PUBLIC_API_URL` 设为 Railway 绝对地址；使用同源 `/api/v1` + `next.config.js` rewrites（见 README）。本地调试可设 `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1`。

#### 或使用 Git 集成：

1. 将代码推送到 GitHub/GitLab
2. 在 Vercel Dashboard 导入项目
3. 配置环境变量
4. 自动部署

---

### 方案二：部署到 Railway

Railway 适合与后端统一部署。

#### 步骤：

1. **创建 Dockerfile**
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
```

2. **创建 railway.json**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "npm start",
    "healthcheckPath": "/",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

3. **在 Railway Dashboard 部署**

---

### 方案三：静态导出

适合部署到任何静态托管服务。

#### 修改 next.config.js：
```javascript
const nextConfig = {
  output: 'export',
  distDir: 'dist',
  images: {
    unoptimized: true,
  },
}
```

#### 构建：
```bash
npm run build
```

#### 部署到 Netlify：
```bash
npm i -g netlify-cli
netlify deploy --prod --dir=dist
```

---

## 配置说明

### 环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `NEXT_PUBLIC_API_URL` | 可选。仅本地直连后端时设为 `http://127.0.0.1:8000/api/v1`；**生产勿设为 Railway** |
| `RAILWAY_API_ORIGIN` | 可选。Next rewrites 转发目标，默认 `https://ai-native-ip-production.up.railway.app` |

### next.config.js 配置

```javascript
const nextConfig = {
  reactStrictMode: true,
  
  // API 代理配置
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'https://ai-native-ip-production.up.railway.app/api/:path*',
      },
    ];
  },
  
  // 图片域名配置（如有需要）
  images: {
    domains: ['ai-native-ip-production.up.railway.app'],
  },
  
  // CORS 配置
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
        ],
      },
    ];
  },
}
```

---

## 验证部署

### 1. 检查首页
访问部署后的域名，应看到 Dashboard 页面。

### 2. 检查 API 连接
打开浏览器开发者工具，Network 标签页应看到：
- 请求发送到 `/api/v1/...`
- 响应状态 200

### 3. 功能测试
- 创建IP
- 录入素材
- 搜索素材

---

## 故障排查

### 问题：API 请求 404
**原因**: API 代理配置错误
**解决**: 检查 `next.config.js` 中的 rewrites 配置

### 问题：样式丢失
**原因**: Tailwind 构建失败
**解决**: 
```bash
rm -rf .next
npm run build
```

### 问题：字体加载失败
**原因**: Google Fonts 访问问题
**解决**: 将字体文件下载到本地或使用系统字体

---

## 性能优化

### 1. 启用图片优化
```javascript
// next.config.js
images: {
  domains: ['your-cdn.com'],
  formats: ['image/webp'],
}
```

### 2. 代码分割
Next.js 自动进行代码分割，无需额外配置。

### 3. 缓存策略
```javascript
// next.config.js
async headers() {
  return [
    {
      source: '/(.*)',
      headers: [
        {
          key: 'Cache-Control',
          value: 'public, max-age=3600, must-revalidate',
        },
      ],
    },
  ];
}
```

---

## 监控

### Vercel Analytics
在 Vercel Dashboard 中启用 Web Analytics。

### 自定义监控
```javascript
// 在关键操作处添加
console.log('[Analytics]', { action: 'create_ip', ip_id: '...' });
```

---

## 更新部署

### 自动部署（推荐）
配置 Git 集成后，推送到主分支自动触发部署。

### 手动部署
```bash
cd frontend
vercel --prod
```

---

## 域名配置

### Vercel 自定义域名
1. 在 Vercel Dashboard → Settings → Domains
2. 添加域名
3. 配置 DNS 记录

### Railway 自定义域名
1. 在 Railway Dashboard → Settings
2. 添加自定义域名
3. 配置 CNAME 记录
