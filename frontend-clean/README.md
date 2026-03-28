# AI-Native IP 工厂 - 前端

工业化内容生产系统的前端界面，采用硅谷顶级AI风格设计。

🔗 **后端API**: https://ai-native-ip-production.up.railway.app  
📖 **API文档**: https://ai-native-ip-production.up.railway.app/docs

## 🎨 设计特点

- **深色主题**: 优雅的深色背景 (#0a0a0f)
- **渐变色彩**: 紫色-青色-粉色渐变
- **玻璃态效果**: 毛玻璃背景和卡片
- **发光效果**: 按钮和卡片的柔和阴影
- **高对比度**: 清晰的视觉层次

## 🚀 快速开始

```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量（可选）
copy .env.example .env.local

# 启动开发服务器
npm run dev
```

访问 http://localhost:3000

## 📦 部署

### 部署到 Netlify（推荐）

#### 方法一：Git 集成（自动部署）

1. 推送代码到 GitHub
2. 在 [Netlify](https://app.netlify.com/) 导入项目
3. 构建设置见 `netlify.toml`：**不要**在 Netlify 环境变量里把 `NEXT_PUBLIC_API_URL` 设为 Railway 绝对地址；默认走同源 `/api/v1`，由 `next.config.js` 在服务端转发到后端（无浏览器跨域、无边缘代理 502）
4. 点击部署

#### 方法二：CLI 部署

```bash
# 安装 Netlify CLI
npm install -g netlify-cli

# 登录
netlify login

# 部署
netlify deploy --build --prod
```

#### 方法三：PowerShell 脚本

```powershell
# Windows 用户
.\scripts\deploy.ps1
```

详细配置请参考 [DEPLOY_NETLIFY.md](./DEPLOY_NETLIFY.md)

### 部署到 Vercel

```bash
npm i -g vercel
vercel --prod
```

### 部署到 Railway

```bash
# 查看 DEPLOY.md 完整指南
```

## 📁 项目结构

```
frontend/
├── app/                    # Next.js App Router
│   ├── page.tsx           # Dashboard仪表盘
│   ├── ip/                # IP管理
│   ├── agents/            # Agent配置
│   └── config/            # 配置中心
├── components/
│   ├── ui/                # 基础UI组件
│   ├── layout/            # 布局组件
│   └── dashboard/         # 仪表盘组件
├── lib/
│   ├── api.ts             # API客户端
│   └── utils.ts           # 工具函数
├── types/
│   └── index.ts           # TypeScript类型
└── netlify.toml           # Netlify配置
```

## 🔌 API 集成（与 CORS / 502）

- **浏览器**只请求同源路径：`/api/v1/...`（见 `lib/apiBaseUrl.ts`）。
- **`app/api/v1/[[...path]]/route.ts`** 在服务端用 `fetch` 转发到 Railway（`RAILWAY_API_ORIGIN`，默认生产域名），并设置 `maxDuration`；不再依赖 `next.config` 的 rewrites（在 Netlify 上曾出现 502）。
- **勿**在 Netlify 环境变量里设置 `NEXT_PUBLIC_API_URL` 为 Railway 地址；若已误设，代码会在 **`*.netlify.app` / `*.vercel.app` 上强制使用同源 `/api/v1`**（见 `lib/apiBaseUrl.ts`），但仍需重新部署后生效。

## 🛠️ 技术栈

- **框架**: Next.js 14 (App Router)
- **语言**: TypeScript
- **样式**: Tailwind CSS
- **字体**: Inter + JetBrains Mono
- **图标**: Lucide React

## 📱 功能页面

| 页面 | 功能 |
|------|------|
| Dashboard | 关键指标、Agent状态、工作流 |
| IP管理 | IP列表、创建、统计 |
| Agent工作流 | 7-Agent配置总览 |
| Memory Agent | 素材录入、语义检索、标签管理 |
| 配置中心 | 全局设置、配置历史 |

## 📚 文档

- [部署到 Netlify](./DEPLOY_NETLIFY.md)
- [通用部署指南](./DEPLOY.md)

## 🔧 环境变量

- 生产：**一般无需** `NEXT_PUBLIC_API_URL`。
- 本地连本机后端：`.env.local` 中 `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1`。
- 覆盖转发目标：`RAILWAY_API_ORIGIN`（与 `next.config.js` 一致）。

## 📄 许可证

MIT
