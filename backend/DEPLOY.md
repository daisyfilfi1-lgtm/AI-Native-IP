# Railway 部署说明

本后端通过 **Railway** 从 GitHub 自动构建并部署，无需本地 Docker，部署后获得公网 HTTPS 地址，便于第三方联调测试。

**当前部署范围**：仅 **后端 API 服务**。打开公网域名会看到产品说明页（含 API 文档入口）；完整的「Agent 配置中心」前端界面为后续规划，尚未一并部署。

---

## 前提

- 代码已推送到 **GitHub** 仓库
- 注册 [Railway](https://railway.app)，使用 **GitHub 登录**

---

## 一、创建项目并部署

1. 打开 [Railway Dashboard](https://railway.app/dashboard) → **New Project**。
2. 选择 **Deploy from GitHub repo**，授权 Railway 访问 GitHub，选中本仓库。
3. **构建方式二选一**：  
   - **方式 A**：在该 Web 服务的 **Settings → Root Directory** 中填写 **`backend`**，保存。构建会使用 `backend/Procfile` 和 `backend/requirements.txt`。  
   - **方式 B**：不设置 Root Directory，使用仓库根目录的 **Dockerfile**（会从 `backend/` 拷贝并构建），平台会自动识别并完成构建。
4. **添加 PostgreSQL**：在同一项目里点击 **New → Database → PostgreSQL**。创建后 Railway 会生成数据库，并在项目内暴露 `DATABASE_URL`。若 Web 服务未自动获得该变量，到 Web 服务 **Variables** 中添加：`DATABASE_URL` = `${{Postgres.DATABASE_URL}}`（或按面板上该数据库的变量引用名称填写）。
5. **部署**：Railway 会识别 `Procfile` 中的 `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT` 并启动服务。首次推送或点击 **Deploy** 后等待构建完成。
6. **生成公网域名**：在 Web 服务 **Settings → Networking → Generate Domain**，得到类似 `xxx.up.railway.app` 的 HTTPS 地址。

---

## 二、数据库迁移（已自动执行）

表结构在**每次容器启动时**会自动执行迁移（`Dockerfile` 中已配置：先跑 `scripts/run_migrations.py` 再启动 uvicorn）。无需在本地安装 Railway CLI 或手动执行迁移。若需在本地用 Railway 环境跑迁移，可执行：`railway login` → `railway link` → `cd backend` → `railway run python scripts/run_migrations.py`。

---

## 三、验证

| 用途       | 地址 |
|------------|------|
| 产品说明页（首页） | `https://你的域名/` |
| 健康检查   | `https://你的域名/health` |
| API 文档   | `https://你的域名/docs` |
| 创建 IP 示例 | `POST https://你的域名/api/v1/ip`，Body: `{"ip_id":"test_001","name":"测试IP","owner_user_id":"user_001"}` |

迁移已在部署时自动执行；若曾部署过早于“自动迁移”的版本，可触发一次重新部署以完成建表。

---

## 四、环境变量

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | PostgreSQL 连接串，由 Railway 在添加 PostgreSQL 后自动注入；若为 `postgres://` 开头，应用内会自动转为 `postgresql://`。 |
| `PORT` | 由 Railway 注入，无需配置。 |

---

## 五、第三方联调

把部署得到的 **HTTPS 基地址**（如 `https://xxx.up.railway.app`）提供给对方即可：

- 接口前缀：`/api/v1/`
- 交互式文档：`基地址/docs`
- 建议流程：先 `POST /api/v1/ip` 创建 IP，再调用 `/api/v1/memory/ingest`、`/api/v1/config/memory` 等接口。

---

## 六、故障排查

- **502 / 无法访问**：确认该服务的 **Root Directory** 为 `backend`，且启动命令使用 `$PORT`（Procfile 已配置）。
- **数据库连接失败**：确认 Web 服务环境变量中有 `DATABASE_URL`（来自 Postgres 插件或手动引用），且已执行过 `scripts/run_migrations.py`。
- **迁移报错**：确认在 `backend` 目录下执行 `railway run python scripts/run_migrations.py`，且 `db/migrations/` 下存在 `001_init.sql`、`002_ingest_tasks.sql`。
