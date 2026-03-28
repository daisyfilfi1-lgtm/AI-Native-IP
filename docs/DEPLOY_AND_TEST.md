# 前后端部署与联调测试（Railway + 前端托管）

## 一、后端（Railway）

1. 参考 `backend/DEPLOY.md`：Root Directory = `backend`，挂 PostgreSQL，`DATABASE_URL` 已注入。
2. 在 **Variables** 中配置：
   - AI：`OPENAI_API_KEY`、`OPENAI_BASE_URL`（若用 DeepSeek）、`OPENAI_TRANSCRIPTION_*`（若 Whisper 走 OpenAI）等，见 `docs/AI_CONFIG.md`。
   - 对象存储：`STORAGE_*`，阿里云见 `docs/STORAGE_ALIYUN_OSS.md`。
   - 飞书（可选）：`FEISHU_APP_ID`、`FEISHU_APP_SECRET` 或在后台保存凭证。
3. 重新部署后打开：`https://你的域名/docs`，确认无 502。
4. 确认迁移含 `004_storage_and_vectors.sql`（启动时会执行 `scripts/run_migrations.py`）。

## 二、前端（Netlify / Vercel 等）

1. 构建目录选 **`frontend`** 仓库子目录（或单独前端仓库）。
2. 环境变量：**`NEXT_PUBLIC_API_URL`** = `https://你的Railway域名/api/v1`（末尾 **必须** 含 `/api/v1`，与 `frontend/lib/api.ts` 一致）。
3. 部署完成后，在浏览器打开管理后台，走一遍：`IP 管理` → `记忆 Agent` → 录入 / 配置 / 飞书（按需）。

详见 `frontend/DEPLOY_NETLIFY.md`、`frontend/DEPLOY.md`。

## 三、联调最小用例

| 步骤 | 操作 |
|------|------|
| 1 | `POST /api/v1/ip` 创建测试 IP |
| 2 | `POST /api/v1/config/memory` 保存该 IP 的 `tag_config`（可选） |
| 3 | 文本 URL：`POST /api/v1/memory/ingest`；或先 `POST /api/v1/memory/upload` 再 ingest 带 `local_file_id` |
| 4 | `GET /api/v1/memory/assets?ip_id=...` 看素材是否写入 |
| 5 | `POST /api/v1/memory/retrieve` 测检索（有 Embedding 时优先向量） |

更细步骤见 `docs/业务实测指南.md`。

## 四、Git 推送说明

- 若 **前端与后端在同一 monorepo**：一次 `git push` 可同时触发 Railway（backend）与 Netlify（frontend，需分别绑定目录/项目）。
- 若 **前端为独立仓库**：需分别在两个仓库推送或 CI 触发部署。
