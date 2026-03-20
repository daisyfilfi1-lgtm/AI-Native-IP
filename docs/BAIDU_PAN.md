# 百度网盘同步

将百度网盘指定目录下的**文本类文件**（`.txt` / `.md` / `.json` / `.csv` / `.log` / `.yaml` 等）同步到某个 IP 的 Memory（`ip_assets`）。

## 1. 获取 access_token

1. 打开 [百度网盘开放平台](https://pan.baidu.com/union/console/applist)，创建应用并获取 **AppKey / AppSecret**。
2. 按官方文档完成 **OAuth 授权**，取得用户维度的 **access_token**（及 refresh_token，便于续期）。
3. 将 **access_token** 填入后端环境变量或管理后台（与飞书凭证类似）。

> 说明：access_token 会过期，过期后需用 refresh_token 刷新或重新授权。Phase 1 仅存储 access_token，续期流程可在后续版本接入。

## 2. 后端配置

**方式 A：环境变量**

```env
BAIDU_PAN_ACCESS_TOKEN=你的_access_token
```

**方式 B：API（与前端「集成」页面对齐）**

- `GET /api/v1/integrations/baidu/config` — 查看是否已配置（响应中含明文 `access_token`，便于再次编辑）
- `POST /api/v1/integrations/baidu/config` — 保存  
  Body: `{ "access_token": "...", "app_key": "可选" }`

## 3. 触发同步

`POST /api/v1/integrations/baidu/sync`

```json
{
  "ip_id": "你的 IP ID",
  "remote_path": "/",
  "recursive": true
}
```

- `remote_path`：网盘目录，如 `/我的资源/笔记`。
- `recursive`：是否递归子目录（单次同步有文件数量上限，见代码中 `max_files`）。

成功时返回 `synced` / `failed` / `errors`。

## 4. 限制

- 单文件大小默认不超过 **10MB**；仅处理上述文本后缀。
- 与飞书同步类似，同步内容会写入向量索引（若已配置 Embedding）。
