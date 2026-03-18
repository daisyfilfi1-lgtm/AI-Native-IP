## Phase 1：AI-Native IP 工厂后端与数据设计（草案）

本文件覆盖 Phase 1 的 4 个基础设计项：

1. 统一领域模型（运行时数据 + 配置数据）
2. 后端与云端 API 技术栈选型
3. Phase 1 API 设计（接口清单与请求/响应结构）
4. Phase 1 数据库 Schema 草案（DDL 级别）

---

## 1. 统一领域模型（Domain Model）

### 1.1 核心实体与关系概览

- `IP`
  - 描述一个 IP 主体（个人或品牌），所有资产、配置都挂在 `ip_id` 之下。
- `IPAsset`
  - Memory Agent 的核心输出：结构化素材资产（故事、观点、数据等）。
- `TagConfig`
  - Memory Agent 的标签体系配置，用于控制自动打标与人工打标选项。
- `MemoryConfig`
  - Memory Agent 的检索/使用策略配置（top_k、相似度阈值、使用频次限制等）。
- `ContentDraft`
  - 后续 Phase（Remix/Generation）的统一内容草稿模型，Phase 1 可以只使用其中与 Memory 相关的字段或预留表结构。
- `ConfigHistory`
  - 所有 Agent 配置的版本历史记录（通用表或按模块拆表）。
- `User` / `Role` / `Permission`
  - Agent 配置中心后台用户及权限模型，Phase 1 只用到最小子集（超级管理员、IP 主理人）。

关系（简写）：

- 一个 `IP` 拥有多条 `IPAsset`
- 一个 `IP` 拥有 0~1 套 `TagConfig`、`MemoryConfig`
- 一个 `User` 可以归属多个 `IP`（例如服务商代运营），但 Phase 1 可先简化为 “一个用户负责一个或多个 IP”

### 1.2 运行时数据模型（Runtime Models）

#### 1.2.1 IP

用于区分不同 IP、多租户边界。

```yaml
IP:
  ip_id: string          # 主键，例如: "zhangkai_001"
  name: string           # 展示名
  owner_user_id: string  # 归属用户
  status: string         # active / inactive
  created_at: datetime
  updated_at: datetime
```

#### 1.2.2 IPAsset（与 PRD 对齐）

```yaml
IPAsset:
  asset_id: string               # 主键，例如: "story_003"
  ip_id: string                  # 归属 IP
  asset_type: string             # story | opinion | joke | data
  title: string                  # 素材标题
  content: text                  # 文本内容
  content_vector: float[]        # 向量（存向量库，DB 存引用或冗余前几维）
  metadata:
    emotion_tags: string[]       # 情绪标签
    scene_tags: string[]         # 场景标签
    cognitive_tags: string[]     # 认知标签
    product_relevance: string    # high/mid/low/none
    usage_count: int             # 已使用次数
    usage_limit: int | null      # 使用上限，null 表示不限
    is_core: bool                # 是否核心素材
    source: string               # 来源标识，如原始文件 ID
    audio_timeline: float[2] | null  # 起止时间（秒）
  relations:                     # 知识图谱关系（Phase 1 可不强依赖）
    - type: string               # LEADS_TO / CONTRADICTS 等
      target_asset_id: string
  status: string                 # active / pending / archived
  created_at: datetime
  updated_at: datetime
```

#### 1.2.3 ContentDraft（预留，Phase 1 可不必完全实现）

```yaml
ContentDraft:
  draft_id: string
  ip_id: string
  level: string                  # A|B|C
  workflow:
    source_topic_id: string | null
    competitor_urls: string[] | null
    remix_version: string | null
    generation_model: string | null
    assets_used: string[]        # 引用的 IPAsset.asset_id 列表
  quality_score:
    originality: float | null
    ip_similarity: float | null
    emotion_curve: float | null
    predicted_completion: float | null
  compliance_status: string      # pending | passed | failed | warning
  created_at: datetime
  updated_at: datetime
```

### 1.3 配置数据模型（Config Models）

所有配置都挂在 `{ip_id, agent_type}` 下面，后端对外通过统一接口：

- `GET /api/v1/config/{agent_type}?ip_id=xxx`
- `POST /api/v1/config/{agent_type}`

#### 1.3.1 TagConfig（标签配置，与 PRD 对齐）

```yaml
TagConfig:
  config_id: string
  ip_id: string
  tag_categories:
    - name: string              # "情绪标签"
      level: int                # 1/2/3
      type: string              # multi_select | single_select
      values:
        - value: string         # "anger"
          label: string         # "愤怒"
          color: string         # "#FF4D4F"
          enabled: bool         # 是否可用
  version: int
  updated_by: string
  updated_at: datetime
```

#### 1.3.2 MemoryConfig（检索与使用策略配置）

```yaml
MemoryConfig:
  config_id: string
  ip_id: string
  retrieval:
    strategy: string            # vector / keyword / hybrid
    top_k: int                  # 3~5
    min_similarity: float       # 0.8~0.9
    diversity_enabled: bool
    diversity_recent_window: int
    freshness_weight: int       # 0~50 (%)
  usage_limits:
    core_max_usage: int
    normal_max_usage: int
    disposable_max_usage: int
    exceed_behavior: string     # block | warn
  version: int
  updated_by: string
  updated_at: datetime
```

#### 1.3.3 ConfigHistory（通用配置历史）

```yaml
ConfigHistory:
  id: string
  ip_id: string
  agent_type: string            # memory / strategy / generation / ...
  version: int
  config_json: jsonb
  changed_by: string
  changed_at: datetime
```

---

## 2. 后端与云端 API 技术栈选型（Phase 1）

### 2.1 后端基础栈

- 语言与框架：Python + FastAPI
- 任务队列：Celery + Redis
- 主数据库：PostgreSQL
- 身份认证：JWT（用户登录）+ IP 级别权限控制
- 日志与监控：结构化日志（JSON），之后对接集中日志系统

### 2.2 云端 AI/向量服务（建议）

- ASR：
  - 优先：OpenAI Whisper API 或等价云服务（具体按成本与可用性最终确定）。
- Embedding：
  - 优先：高维文本嵌入模型（如 text-embedding-3-large 或等价服务）。
- LLM（用于自动打标等）：
  - 轻量模型（如 Claude Haiku / GPT-4-mini / 国产轻量模型），按成本优化。
- 向量库：
  - Phase 1：外部向量服务（如 Pinecone / Qdrant Cloud），使用 `namespace = ip_id` 做隔离。

### 2.3 部署模式

- 走“云端 API 模式”：所有模型推理通过第三方 API 完成，后端只负责编排。
- Phase 1 聚焦单 Region 部署，后续再考虑多 Region、高可用。

---

## 3. Phase 1 API 设计（Memory 相关）

命名空间统一为：`/api/v1`

### 3.1 素材录入：POST /memory/ingest

**用途**：接收素材，触发后台转写 / 向量化 / 自动打标流水线。

```http
POST /api/v1/memory/ingest
Content-Type: application/json

Request:
{
  "ip_id": "zhangkai_001",
  "source_type": "video",          # video|audio|text|document
  "source_url": "https://...mp4",  # 远程 URL，或
  "local_file_id": null,           # 由上传中心生成的文件 ID（可选）
  "title": "2020破产夜",
  "notes": "那次关键的翻盘经历"       # 供打标参考的备注（可选）
}

Response:
{
  "ingest_task_id": "ingest_20260317_0001",
  "status": "QUEUED"
}
```

### 3.2 素材处理结果查询：GET /memory/ingest/{task_id}

```http
GET /api/v1/memory/ingest/{task_id}

Response:
{
  "ingest_task_id": "ingest_20260317_0001",
  "status": "PROCESSING",      # QUEUED|PROCESSING|FAILED|COMPLETED
  "error": null,
  "created_assets": ["story_003"]  # 完成后返回 asset_id 列表
}
```

### 3.3 语义检索：POST /memory/retrieve

```http
POST /api/v1/memory/retrieve
Content-Type: application/json

Request:
{
  "ip_id": "zhangkai_001",
  "query": "深夜崩溃但最终翻盘的故事",
  "filters": {
    "emotion_tags": ["despair", "hope"],
    "scene_tags": ["night"],
    "max_usage_ratio": 0.8      # 可选，usage_count/usage_limit < 0.8
  },
  "top_k": 3                    # 可选，默认使用 MemoryConfig 中的 top_k
}

Response:
{
  "results": [
    {
      "asset_id": "story_003",
      "title": "2020年那个深夜",
      "content_snippet": "那天晚上我几乎要放弃了...",
      "metadata": {
        "emotion_tags": ["anger", "despair"],
        "scene_tags": ["night"],
        "usage_count": 2,
        "usage_limit": 3,
        "is_core": true
      },
      "similarity": 0.92
    }
  ]
}
```

### 3.4 自动打标复核列表：GET /memory/pending-labels

```http
GET /api/v1/memory/pending-labels?ip_id=zhangkai_001&limit=20

Response:
{
  "items": [
    {
      "asset_id": "story_003",
      "title": "2020年那个深夜",
      "source": "interview_20240317",
      "content_snippet": "那天晚上我几乎要放弃了...",
      "auto_labels": {
        "emotion_tags": [
          {"value": "anger", "confidence": 0.92},
          {"value": "anxiety", "confidence": 0.45}
        ],
        "scene_tags": [
          {"value": "night", "confidence": 0.98}
        ],
        "cognitive_tags": [
          {"value": "revelation", "confidence": 0.85}
        ]
      }
    }
  ]
}
```

### 3.5 自动打标复核提交：POST /memory/labels/{asset_id}

```http
POST /api/v1/memory/labels/story_003
Content-Type: application/json

Request:
{
  "ip_id": "zhangkai_001",
  "confirmed_labels": {
    "emotion_tags": ["anger", "despair"],
    "scene_tags": ["night"],
    "cognitive_tags": ["revelation"]
  }
}

Response:
{
  "success": true
}
```

### 3.6 配置读取与保存（Memory 专用）

```http
GET /api/v1/config/memory?ip_id=zhangkai_001
POST /api/v1/config/memory
```

请求与响应 JSON 结构直接使用 `MemoryConfig` / `TagConfig` 的定义。

---

## 4. Phase 1 数据库 Schema 草案（PostgreSQL）

> 说明：以下为逻辑 DDL 草案，后续可以拆分为真正的 SQL 文件。

### 4.1 表：ip

```sql
CREATE TABLE ip (
  ip_id        VARCHAR(64) PRIMARY KEY,
  name         VARCHAR(255) NOT NULL,
  owner_user_id VARCHAR(64) NOT NULL,
  status       VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 4.2 表：ip_assets

```sql
CREATE TABLE ip_assets (
  asset_id      VARCHAR(64) PRIMARY KEY,
  ip_id         VARCHAR(64) NOT NULL,
  asset_type    VARCHAR(32) NOT NULL,
  title         VARCHAR(255),
  content       TEXT NOT NULL,
  content_vector_ref VARCHAR(128),        -- 向量库中的 ID/namespace
  metadata      JSONB NOT NULL DEFAULT '{}',
  relations     JSONB NOT NULL DEFAULT '[]',
  status        VARCHAR(32) NOT NULL DEFAULT 'active',
  created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_ip_assets_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);

CREATE INDEX idx_ip_assets_ip_id ON ip_assets(ip_id);
CREATE INDEX idx_ip_assets_status ON ip_assets(status);
CREATE INDEX idx_ip_assets_metadata_gin ON ip_assets USING GIN (metadata);
```

### 4.3 表：tag_config

```sql
CREATE TABLE tag_config (
  config_id    VARCHAR(64) PRIMARY KEY,
  ip_id        VARCHAR(64) NOT NULL UNIQUE,
  tag_categories JSONB NOT NULL,
  version      INT NOT NULL DEFAULT 1,
  updated_by   VARCHAR(64) NOT NULL,
  updated_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_tag_config_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);
```

### 4.4 表：memory_config

```sql
CREATE TABLE memory_config (
  config_id    VARCHAR(64) PRIMARY KEY,
  ip_id        VARCHAR(64) NOT NULL UNIQUE,
  retrieval    JSONB NOT NULL,
  usage_limits JSONB NOT NULL,
  version      INT NOT NULL DEFAULT 1,
  updated_by   VARCHAR(64) NOT NULL,
  updated_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_memory_config_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);
```

### 4.5 表：config_history

```sql
CREATE TABLE config_history (
  id           VARCHAR(64) PRIMARY KEY,
  ip_id        VARCHAR(64) NOT NULL,
  agent_type   VARCHAR(64) NOT NULL,
  version      INT NOT NULL,
  config_json  JSONB NOT NULL,
  changed_by   VARCHAR(64) NOT NULL,
  changed_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_config_history_ip_agent ON config_history(ip_id, agent_type);
```

### 4.6 表：content_drafts（预留，Phase 1 可选）

```sql
CREATE TABLE content_drafts (
  draft_id      VARCHAR(64) PRIMARY KEY,
  ip_id         VARCHAR(64) NOT NULL,
  level         VARCHAR(8) NOT NULL,
  workflow      JSONB NOT NULL,
  quality_score JSONB NOT NULL,
  compliance_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_content_drafts_ip FOREIGN KEY (ip_id) REFERENCES ip(ip_id)
);

CREATE INDEX idx_content_drafts_ip_id ON content_drafts(ip_id);
```

---

（以上为 Phase 1 设计基础草案，后续可以根据实现细节迭代。）

