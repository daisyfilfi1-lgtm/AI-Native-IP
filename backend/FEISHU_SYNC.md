# 飞书知识库同步

将飞书知识库中的文档同步到 AI-Native IP 的 Memory（ip_assets），供后续检索与生成使用。

> 另：**百度网盘**目录同步见项目根目录 `docs/BAIDU_PAN.md`。

## 1. 飞书开放平台配置

1. 登录 [飞书开放平台](https://open.feishu.cn)，创建企业自建应用。
2. **凭证与安全**：在「凭证与基础信息」中获取 **App ID**、**App Secret**，用于环境变量。
3. **权限**：在「权限管理」中为应用开通（你已开通的即可用）：
   - `wiki:space:read` 或 `wiki:wiki`：查看知识空间列表
   - `wiki:node:read` 或 `wiki:wiki`：查看知识空间节点（文档列表）
   - 获取文档**纯文本内容**还需：
     - **旧版文档 (doc)**：云文档相关权限（如 `drive:drive:readonly` 或文档只读权限）
     - **新版文档 (docx)**：若同步时报错无权限，请在开放平台申请 **「查看、评论和下载云空间中所有文件」** 或文档类只读权限
4. **知识库授权**：将应用添加为要同步的**知识库成员**（至少可读），否则列表/内容会为空或 131006 权限错误。  
   路径：知识库 → 设置 → 成员与权限 → 添加成员 → 选择该应用。

## 2. 凭证配置（二选一）

- **推荐**：在管理后台 **记忆 Agent → 飞书同步** 页签中，在「飞书应用凭证」卡片填写 **App ID**、**App Secret** 并点击「保存凭证」。凭证会保存在本系统数据库，后续列空间、同步均优先使用此处配置。
- **可选**：在 **Railway** 的 Web 服务 **Variables** 中新增（或本地 `.env`）：
  - `FEISHU_APP_ID`、`FEISHU_APP_SECRET`  
  若管理后台未保存凭证，则使用环境变量。

## 3. 接口说明

- **GET /api/v1/integrations/feishu/config**  
  获取飞书配置状态（是否已配置、**完整 app_id** 便于再次编辑；secret 不返回），供管理后台展示。

- **POST /api/v1/integrations/feishu/config**  
  保存飞书凭证（管理后台填写）。Body：`{ "app_id": "xxx", "app_secret": "xxx" }`。

- **GET /api/v1/integrations/feishu/spaces**  
  列出当前应用有权限的知识空间，返回 `space_id`、`name` 等，用于确认要同步的空间。

- **GET /api/v1/integrations/feishu/binding?ip_id=...**  
  读取某个 IP 的默认飞书空间映射（若已配置）。

- **POST /api/v1/integrations/feishu/binding**  
  保存某个 IP 的默认空间映射。Body：`{ "ip_id":"test_001", "space_id":"...", "space_name":"可选" }`。

- **POST /api/v1/integrations/feishu/sync**  
  触发一次同步。  
  Body 示例：
  ```json
  { "ip_id": "test_001", "space_id": "可选，不传则用第一个空间" }
  ```
  响应示例：
  ```json
  { "synced": 10, "failed": 0, "errors": [], "used_space_id": "..." }
  ```
  会将该空间下所有 **doc / docx** 节点拉取为纯文本，按标题做结构化分段后写入/更新到指定 `ip_id` 的 `ip_assets`（asset_type=`data`，source=feishu_kb，metadata 内含 `doc_title`、`section_title`、`chunk_index`、`outline` 等）。

## 4. 使用流程

1. 在系统中先创建 IP：`POST /api/v1/ip`（若尚未创建）。
2. 配置并部署好 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`。
3. 可选：调用 `GET /api/v1/integrations/feishu/spaces` 确认能看到目标知识库。
4. 调用 `POST /api/v1/integrations/feishu/sync`，传入 `ip_id`（及可选 `space_id`）。
5. 同步完成后，该 IP 的 Memory 检索与素材录入即可使用这些文档内容。

## 5. 可选权限（若同步 doc/docx 报错）

若接口返回「无权限」或 content 为空：

- 在飞书开放平台为应用补充：
  - **查看、评论和下载云空间中所有文件**（`drive:drive:readonly`，你已开通），或
  - 文档/云文档的只读类权限（具体以开放平台文档为准）。
- 再次确认应用已被添加为目标知识库的成员。
