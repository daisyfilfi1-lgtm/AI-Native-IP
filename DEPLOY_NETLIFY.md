# 部署到 Netlify 指南

Netlify 是部署 Next.js 应用的优秀平台，提供全球 CDN、自动部署和边缘函数支持。

## 🚀 快速部署

### 方法一：通过 Git 部署（推荐）

1. **推送代码到 GitHub**
```bash
cd frontend
git init
git add .
git commit -m "Initial commit"
gh repo create ai-native-ip-frontend --public --push
```

2. **在 Netlify 部署**
   - 访问 [Netlify](https://app.netlify.com/)
   - 点击 "Add new site" → "Import an existing project"
   - 选择 GitHub 仓库
   - 构建设置会自动识别（使用 netlify.toml）
   - 点击 "Deploy site"

### 方法二：使用 Netlify CLI

1. **安装 CLI**
```bash
npm install -g netlify-cli
```

2. **登录**
```bash
netlify login
```

3. **初始化项目**
```bash
netlify init
```

4. **部署**
```bash
# 预览部署
netlify deploy --build

# 生产部署
netlify deploy --build --prod
```

### 方法三：拖拽部署（静态导出）

1. **修改 next.config.js 为静态导出**
```javascript
const nextConfig = {
  output: 'export',
  distDir: 'dist',
  images: {
    unoptimized: true,
  },
  // 移除 rewrites，使用 _redirects 文件
}
```

2. **创建 _redirects 文件**
```
/api/*  https://ai-native-ip-production.up.railway.app/api/:splat  200
/*      /index.html                                                200
```

3. **构建并部署**
```bash
npm run build
# 将 dist 文件夹拖拽到 Netlify 控制台
```

---

## ⚙️ 配置说明

### Netlify 控制台 Build 设置（必须与仓库一致）

仓库 **`daisyfilfi1-lgtm/ai-native-ip-frontend`** 里 Next.js 在**仓库根目录**（`app/`、`package.json` 在根上），**没有**用于部署的 `frontend/` 子目录；本地 `frontend/` 若在 `.gitignore` 中，也不会出现在 GitHub。

在 Netlify：**Site configuration → Build & deploy → Build settings**（或新 UI 的 **Build** 区块）请设为：

| 项 | 正确值 | 错误示例（会导致配置/构建失败） |
|----|--------|--------------------------------|
| **Base directory** | **留空**（使用仓库根） | `frontend` |
| **Build command** | `npm run build` | — |
| **Publish directory** | `.next`（或由 `@netlify/plugin-nextjs` 接管；以控制台说明为准） | `frontend/.next` |
| **Package directory** | 留空 | 指到不存在的子目录 |

保存后重新部署。根目录 `netlify.toml` 里已设 `[build] base = "."`，用于锁定在仓库根构建；**请勿**在控制台再填 Base = `frontend`。

### netlify.toml 与 API（重要）

- **应使用** `netlify.toml` 里 `[[redirects]] from="/api/*"` **边缘代理**到 Railway（`status = 200`）。请求**不经过** Next.js Serverless 函数，可避免免费版 **约 10s 函数超时** → 轮询 `GET /memory/ingest/...`、大文件上传时出现 **502 `Application failed to respond`**。
- **不要**使用 `/* → /index.html` 作为 SPA 回退（会破坏 Next.js App Router）。
- **不要**再使用 `app/api/v1/.../route.ts` 做服务端 fetch 代理（会与上述策略重复，且易触发 Serverless 超时）。
- **本地开发**：`next.config.js` 的 `rewrites` 把 `/api/v1/*` 转到 `RAILWAY_API_ORIGIN` 或 `http://127.0.0.1:8000`；**生产**由 Netlify 边缘规则处理。
- **浏览器**仍请求同源 `/api/v1/...`，一般**无**跨域问题；若 Railway 宕机仍可能 502，需看 Railway 日志。

### 环境变量配置

在 Netlify → Site settings → Environment variables：

1. **删除**（若存在）`NEXT_PUBLIC_API_URL` 指向 Railway 的绝对地址——否则会强制 axios 跨域直连，重新出现 **CORS + 502** 组合问题。
2. **生产**：`netlify.toml` 里 `[[redirects]]` 的 Railway 主机名须与当前部署一致；改 Railway 域名后请同步修改并重新部署。本地开发可在 `.env.local` 设 `RAILWAY_API_ORIGIN`（与 `next.config.js` rewrites 一致）。

本地开发连本机后端：在项目根 `.env.local` 中：

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
```

（仅开发时使用；生产不要设置 `NEXT_PUBLIC_API_URL` 为 Railway URL。）

### ⚠️ 文件上传内存问题（重要）

**问题**：上传小文件（如 11KB）时，Railway 内存突然飙升至 4GB。

**原因**：
1. 请求可能经过 Next.js Serverless 函数，而非边缘代理
2. multipart/form-data 在 Serverless 环境中可能导致内存异常
3. 本地 Embedding 模型意外加载（如果 API 失败）

**解决方案**：

1. **确保浏览器直连 Railway**（已配置在 `netlify.toml`）：
   ```toml
   [build.environment]
     NEXT_PUBLIC_API_DIRECT_ORIGIN = "https://your-app.up.railway.app"
   ```

2. **验证直连是否生效**：
   - 浏览器 DevTools → Network → 检查上传请求的 URL
   - ✅ 正确：`https://your-app.up.railway.app/api/v1/memory/upload`
   - ❌ 错误：`https://your-site.netlify.app/api/v1/memory/upload`

3. **后端文件大小限制**（已在代码中配置）：
   - 单文件最大 10MB
   - 流式分块读取（64KB chunks）
   - 内存监控日志

4. **禁用本地 Embedding**（Railway 环境变量）：
   ```
   LOCAL_EMBEDDING_ENABLED = false
   ```

更多详情参见 `docs/MEMORY_ISSUE_FIX.md`。

---

## 🔧 注意事项

### 1. Next.js 运行时

Netlify 使用 `@netlify/plugin-nextjs` 自动支持：
- ✅ Server-Side Rendering (SSR)
- ✅ API Routes
- ✅ Image Optimization
- ✅ Middleware
- ✅ Rewrites/Redirects

### 2. 图片优化

如果使用 Next.js Image 组件，需要在 `next.config.js` 中配置：

```javascript
images = {
  remotePatterns: [
    {
      protocol: 'https',
      hostname: 'ai-native-ip-production.up.railway.app',
    },
  ],
}
```

### 3. 缓存策略

已在 `netlify.toml` 中配置静态资源长期缓存：
- JS/CSS: 1年
- 图片/字体: 1年

### 4. 预览部署

每个 Pull Request 会自动创建预览链接，方便测试。

---

## 🌐 自定义域名

1. 在 Netlify Dashboard → Domain settings
2. 点击 "Add custom domain"
3. 输入你的域名（如 `ip-factory.yourdomain.com`）
4. 按照提示配置 DNS

### DNS 配置示例（Cloudflare）

| Type | Name | Value | TTL |
|------|------|-------|-----|
| CNAME | ip-factory | your-site.netlify.app | Auto |

---

## 🛠️ 故障排查

### 问题：构建失败

**检查点**：
```bash
# 本地测试构建
npm run build

# 检查 Node 版本
node -v  # 需要 18+
```

**常见解决**：
- 在 Netlify Dashboard 设置 Node 版本：`NODE_VERSION = 18`
- 清除缓存重新部署

### 问题：API 请求 404

**检查点**：
- 确认 `netlify.toml` 中的 redirects 配置
- 检查浏览器 Network 面板，确认请求路径是 `/api/...`

**调试**：
```bash
# 本地测试 redirects
netlify dev
```

### 问题：样式丢失

**解决**：
```bash
rm -rf .next node_modules
npm install
npm run build
```

### 问题：图片不显示

**解决**：
```javascript
// next.config.js
images = {
  unoptimized: true,  // 静态导出时使用
}
```

---

## 📊 性能优化

### 启用 Netlify Edge

```toml
# netlify.toml
[build]
  edge_functions = "netlify/edge-functions"
```

### 启用 Analytics

在 Netlify Dashboard → Analytics 中启用，查看：
- 访问量
- 来源分析
- 性能指标

---

## 🔄 持续部署

配置 Git 集成后：

1. **开发分支** → 自动部署预览链接
2. **合并到 main** → 自动部署生产环境
3. **PR 评论** → 自动生成预览链接

---

## 📱 部署状态检查

部署后检查清单：

- [ ] 首页加载正常
- [ ] Dashboard 数据显示
- [ ] 侧边栏导航正常
- [ ] IP 管理页面加载
- [ ] Agent 配置页面加载
- [ ] API 请求成功（浏览器 DevTools → Network）

---

## 💡 最佳实践

1. **使用 Git 集成**：自动部署 + 预览链接
2. **配置分支预览**：main 分支 = 生产，其他分支 = 预览
3. **设置部署通知**：Slack/Email 通知
4. **启用表单检测**：自动处理 HTML 表单
5. **配置重定向规则**：SEO 友好的 URL

---

## 📚 参考资源

- [Netlify Next.js 文档](https://docs.netlify.com/integrations/frameworks/next-js/)
- [Netlify Redirects](https://docs.netlify.com/routing/redirects/)
- [Netlify Headers](https://docs.netlify.com/routing/headers/)
