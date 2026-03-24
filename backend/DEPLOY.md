# Railway 部署说明

本后端通过 **Railway** 从 GitHub 自动构建并部署，无需本地 Docker，部署后获得公网 HTTPS 地址，便于第三方联调测试。

**当前部署范围**：仅 **后端 API 服务**。打开公网域名会看到产品说明页（含 API 文档入口）；完整的「Agent 配置中心」前端界面为后续规划，尚未一并部署。

---

## 升级后部署检查（RQ + 状态机 + pgvector）

| 项目 | 说明 |
|------|------|
| **PostgreSQL** | 必须用 **pgvector 模板**（见下文 4），普通 Postgres 无 `vector` 扩展，迁移 008 会失败 |
| **DATABASE_URL** | 由 pgvector 版 Postgres 提供，注入到 Web 服务 |
| **REDIS_URL** | 可选。配置后 ingest 走 RQ；不配则回退 BackgroundTasks |
| **Worker 服务** | 配置 REDIS_URL 后需单独部署，Start Command = `python scripts/worker.py` |

---

## 前提

- 代码已推送到 **GitHub** 仓库
- 注册 [Railway](https://railway.app)，使用 **GitHub 登录**

---

## 一、创建项目并部署

1. 打开 [Railway Dashboard](https://railway.app/dashboard) → **New Project**。
2. 选择 **Deploy from GitHub repo**，授权 Railway 访问 GitHub，选中本仓库。
3. **构建方式二选一**（勿混用：Root Directory 与 Dockerfile 必须匹配）：  
   - **方式 A（推荐）**：在该 Web 服务的 **Settings → Root Directory** 中填写 **`backend`**，保存。仓库内 **`backend/railway.toml`** 会指定用 **`backend/Dockerfile`** 构建（构建上下文仅为 `backend/`，避免「根目录 Dockerfile 在上下文外」导致构建失败）。容器启动时会执行 `scripts/run_migrations.py` 再启动 uvicorn。可选：在 **Pre-deploy Command** 中再写一次 `python scripts/run_migrations.py`（与镜像内迁移重复，一般可省略）。  
   - **方式 B**：**Root Directory 留空**，使用仓库根目录的 **Dockerfile** 与根目录 **`railway.toml`**；迁移同样在容器启动时执行。
4. **添加 PostgreSQL（必须用 pgvector 版）**：迁移 `008_pgvector.sql` 依赖 `vector` 扩展，**普通 PostgreSQL 模板没有该扩展**。请使用 **pgvector 模板**：
   - 在同一项目内点击 **New → Template** 或 **New → Database**
   - 搜索并选择 **"Postgres with pgVector Engine"**（或访问 [railway.com/deploy/postgres-with-pgvector-engine](https://railway.com/deploy/postgres-with-pgvector-engine)）
   - 部署后 Railway 会暴露 `DATABASE_URL`。在 Web 服务的 **Variables** 中添加：`DATABASE_URL` = `${{Postgres.DATABASE_URL}}`（变量名以实际服务名为准）。
   - 若已存在普通 Postgres：需新建 pgvector 版并迁移数据，或从零开始用 pgvector 模板部署。
5. **部署**：Dockerfile 启动时会先执行迁移再启动 uvicorn。首次推送或点击 **Deploy** 后等待构建完成。
6. **生成公网域名**：在 Web 服务 **Settings → Networking → Generate Domain**，得到类似 `xxx.up.railway.app` 的 HTTPS 地址。

---

## 二、数据库迁移

- **方式 A**：通过 Pre-deploy Command（见上文）在每次部署前自动执行迁移。
- **方式 B**：Dockerfile 在容器启动时先跑 `scripts/run_migrations.py` 再启动 uvicorn。

若需在本地用 Railway 环境手动跑迁移，可执行：`railway login` → `railway link` → `cd backend` → `railway run python scripts/run_migrations.py`。

---

## 三、验证

| 用途       | 地址 |
|------------|------|
| 产品说明页（首页） | `https://你的域名/` |
| 健康检查   | `https://你的域名/health` |
| API 文档   | `https://你的域名/docs` |
| 创建 IP 示例 | `POST https://你的域名/api/v1/ip`，Body: `{"ip_id":"test_001","name":"测试IP","owner_user_id":"user_001"}` |

迁移已在部署时自动执行；若曾部署过早于“自动迁移”的版本，可触发一次重新部署以完成建表。

**素材文件上传（`/api/v1/memory/upload`）** 依赖迁移 **`004_storage_and_vectors.sql`** 中的 `file_objects` 表。若上传返回 503 且提示数据库写入失败，请在数据库中确认该表存在，或重新执行 `python scripts/run_migrations.py`。S3 上传失败时，在未设置 `STORAGE_LOCAL_DISABLED=true` 的情况下会回退写入本地目录（`data/uploads` 或 `STORAGE_LOCAL_PATH`），后续录入流水线会从本地读取同一文件。

---

## 四、环境变量

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | PostgreSQL 连接串，由 Railway 在添加 PostgreSQL 后自动注入；若为 `postgres://` 开头，应用内会自动转为 `postgresql://`。 |
| `PORT` | 由 Railway 注入，无需配置。 |
| `CORS_ORIGINS` | 可选。默认 `*`（与 `CORS_ALLOW_CREDENTIALS` 未开启时配合浏览器跨域）。若前端域名固定，可改为逗号分隔的完整 origin 列表。 |
| `CORS_ALLOW_CREDENTIALS` | 可选。默认 `false`。仅在需带 Cookie 且使用**非** `*` 的 `CORS_ORIGINS` 时设为 `true`。 |
| `OPENAI_*` / `OPENAI_TRANSCRIPTION_*` | AI 打标、Embedding、Whisper；详见 `docs/AI_CONFIG.md`。 |
| `STORAGE_*` | 对象存储（S3 兼容，含阿里云 OSS）；详见 `docs/STORAGE_ALIYUN_OSS.md` 与 `backend/.env.example`。 |
| `FEISHU_*` | 飞书同步（可选）。 |
| `REDIS_URL` | 可选。Redis 连接串；配置后 ingest 任务走 RQ 队列，需单独部署 worker 进程。未配置时回退到 FastAPI BackgroundTasks。 |
| `QDRANT_*` | 向量数据库（可选）；详见下方"五、部署可选服务"。 |
| `NEO4J_*` | 知识图谱（可选）；详见下方"五、部署可选服务"。 |

**RQ Worker（Railway）**：配置 `REDIS_URL` 后，需单独部署 Worker 服务：
1. 在 Railway 项目内 **New → GitHub Repo**，选中同一仓库。
2. 新服务 **Settings → Root Directory** 填 `backend`。
3. **Settings → Deploy** 中设置 **Start Command** 为：`python scripts/worker.py`（覆盖默认 web 启动）。
4. 在 **Variables** 中添加 `REDIS_URL`（见下）、`DATABASE_URL`（与 Web 服务一致，引用同一 Postgres），以及 Web 服务已有的 AI/存储等变量（Worker 执行 ingest 时需要）。
5. 可选：**Settings** 中取消勾选 **Generate Domain**（Worker 不需要公网访问）。

**卡死任务清理（可选）**：建议配置 Cron 每 5 分钟执行 `python scripts/run_stale_task_cleanup.py`，将长期 PROCESSING 且无心跳的任务标记为 TIMEOUT。可通过 `STALE_TASK_THRESHOLD_SECONDS=300` 调整阈值。

## 五、部署可选服务（Qdrant + Neo4j）

### Redis（RQ 队列，可选）

- 在 Railway 项目内点击 **New → Database → Redis**，或 **Marketplace** 搜索 Redis。
- 创建后在 Web 服务与 Worker 的 **Variables** 中添加：`REDIS_URL` = `${{Redis.REDIS_URL}}`（以实际变量名为准）。
- 未配置时，ingest 会回退到 FastAPI BackgroundTasks（可先上线测 API，再加 Redis+Worker）。

### 方案A：使用 Railway 模板（推荐）

1. **Qdrant 向量数据库**
   - 在 Railway Dashboard 点击 **New → Marketplace**
   - 搜索 **Qdrant** 并选择
   - 创建后获取 `QDRANT_URL`（如 `http://qdrant:6333`）
   - 在你的后端服务中添加变量：`QDRANT_URL=http://qdrant:6333`

2. **Neo4j 知识图谱**
   - 在 Railway Dashboard 点击 **New → Marketplace**
   - 搜索 **Neo4j** 并选择
   - 创建后获取连接信息
   - 在你的后端服务中添加变量：
     ```
     NEO4J_URI=bolt://neo4j:7687
     NEO4J_PASSWORD=你的密码
     NEO4J_DATABASE=neo4j
     ```

### 方案B：使用免费云服务

1. **Qdrant Cloud**（有免费额度）
   - 注册 https://cloud.qdrant.io
   - 创建免费 Cluster
   - 获取 URL 和 API Key
   - 在 Railway 环境变量中配置：
     ```
     QDRANT_URL=https://xxx.qdrant.cloud
     QDRANT_API_KEY=你的APIKey
     ```

2. **Neo4j Aura**（有免费额度）
   - 注册 https://neo4j.com/cloud/aura/
   - 创建 Free Tier 数据库
   - 获取连接字符串
   - 在 Railway 环境变量中配置：
     ```
     NEO4J_URI=bolt://xxx.databases.neo4j.io:7687
     NEO4J_PASSWORD=你的密码
     ```

### 服务间通信

在同一 Railway 项目内，服务间通信使用内部域名：
- `http://qdrant:6333`
- `http://neo4j:7687`

部署后首次含 `004_storage_and_vectors.sql` 的镜像会自动跑迁移；若报错，确认 `db/migrations/` 含 `004_storage_and_vectors.sql`。

---

## 五、第三方联调

把部署得到的 **HTTPS 基地址**（如 `https://xxx.up.railway.app`）提供给对方即可：

- 接口前缀：`/api/v1/`
- 交互式文档：`基地址/docs`
- 建议流程：先 `POST /api/v1/ip` 创建 IP，再调用 `/api/v1/memory/ingest`、`/api/v1/config/memory` 等接口。

---

## 六、故障排查

- **构建失败 / 推不上去 / 找不到 Dockerfile**：若 **Root Directory = `backend`**，构建上下文不包含仓库根目录，**不能**再指向根目录的 `Dockerfile`。应使用已提交的 **`backend/Dockerfile`** + **`backend/railway.toml`**，或将 Root Directory 清空并改用根目录 Dockerfile（二选一）。推送后需在 Railway 上 **Redeploy**。
- **502 / 无法访问**：确认启动使用 `$PORT`（Dockerfile / `Procfile` 已配置）；健康检查路径为 **`/health`**（与 `railway.toml` 一致）。
- **方式 A 迁移未执行**：镜像启动命令已含迁移；若仍缺表，可在 **Pre-deploy Command** 增加 `python scripts/run_migrations.py`，或在本地 `railway run python scripts/run_migrations.py`。
- **数据库连接失败**：确认 Web 服务环境变量中有 `DATABASE_URL`（来自 Postgres 插件或 `${{Postgres.DATABASE_URL}}` 引用），且迁移已成功。
- **迁移报错**：在 `backend` 目录下执行 `railway run python scripts/run_migrations.py`，且 `db/migrations/` 下存在 `001`～`008` 等 SQL 文件。若报 `extension "vector" does not exist`，说明数据库非 pgvector 版，需改用 **Postgres with pgVector Engine** 模板。
- **ingest 任务一直 PROCESSING 或进程被 Killed（OOM）**：大文件会产生极多分块；旧版曾对**每一块**各调一次 LLM 打标与 Embedding，易拖垮内存与 CPU。当前实现已改为**单次打标**、**批量 Embedding**、**正文/分块上限**与**分批 `commit`**。若仍吃紧，在环境中下调 `INGEST_MAX_TEXT_CHARS`、`INGEST_MAX_CHUNKS`，必要时略减 `INGEST_EMBED_BATCH_SIZE`；并设置 `OPENAI_HTTP_TIMEOUT` 避免 API 无限挂起。
- **浏览器报 CORS / 跨域被拦**：官方前端（Netlify）应使用 **同源** `/api/v1`，由 Next.js `rewrites` 在服务端转发到本服务，**不依赖**浏览器 CORS。若仍用 `NEXT_PUBLIC_API_URL` 直连 Railway，需正确 CORS；**502** 时网关响应无 CORS 头，会表现为 CORS+502 叠加——优先修部署稳定性或改回同源代理。后端默认对 `*.netlify.app` 等放行；直连工具可设 `CORS_ORIGINS=*`。
