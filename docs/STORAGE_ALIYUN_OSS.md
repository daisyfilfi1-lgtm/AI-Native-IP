# 阿里云 OSS（S3 兼容）+ Railway 配置说明

后端通过 **boto3** 走 OSS 的 **S3 兼容 API**，与 AWS S3、MinIO 使用同一套环境变量。

## Railway 上需要配置的变量

在 Railway Web 服务 **Variables** 中添加：

| 变量 | 说明 |
|------|------|
| `STORAGE_ENDPOINT` | 地域 Endpoint，**必须带 https://**。例：`https://oss-cn-shanghai.aliyuncs.com`（以控制台为准） |
| `STORAGE_ACCESS_KEY` | RAM 子用户的 AccessKey ID |
| `STORAGE_SECRET_KEY` | RAM 子用户的 AccessKey Secret |
| `STORAGE_BUCKET` | Bucket 名称（与 Endpoint 地域一致） |
| `STORAGE_REGION` | 地域 ID。例：上海 `cn-shanghai`，杭州 `cn-hangzhou` |
| `STORAGE_FORCE_PATH_STYLE` | 建议 **`true`** |
| `STORAGE_PUBLIC_BASE_URL` | **可选**。自定义域名或 CDN 前缀，用于返回可直连的 file_url |

请使用 **RAM 子用户**，权限最小化（仅目标 Bucket 读写）。

## 常见问题

1. **403 SignatureDoesNotMatch**：核对 Secret、Endpoint 是否含 https、REGION 是否与 Bucket 一致。
2. **403 AccessDenied**：检查 RAM 策略是否覆盖该 Bucket。
3. **file_url 浏览器 403**：Bucket 私有时直链不可访问属正常；可绑域名与 CDN，或后续做鉴权下载。
4. **向量检索**：依赖 Embedding 配置；未配置时检索回退关键词。

## 部署后自测

1. `GET /health`
2. Swagger：`POST /memory/upload`（需已创建 IP）
3. `POST /memory/ingest` 带 `local_file_id`

详见 `docs/业务实测指南.md`、`backend/DEPLOY.md`。
