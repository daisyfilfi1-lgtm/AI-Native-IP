# AI-Native IP 工厂后端（Phase 1）

Phase 1 范围：素材进入 → Memory Agent 结构化。本后端提供 Memory 相关 API 与配置中心接口。

**线上部署（无本地 Docker）**：见 [DEPLOY.md](./DEPLOY.md)，按 **Railway** 方案部署到云平台，便于第三方联调测试。  
**飞书知识库同步**：见 [FEISHU_SYNC.md](./FEISHU_SYNC.md)，配置 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 后即可将知识库同步到 IP Memory。

## 环境要求

- Python 3.10+
- PostgreSQL 14+

## 本地运行

### 1. 创建虚拟环境并安装依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### 2. 配置环境变量

复制示例配置并修改：

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

编辑 `.env`，至少设置：

- `DATABASE_URL`：PostgreSQL 连接串，例如  
  `postgresql://user:password@localhost:5432/ip_factory`

### 3. 初始化数据库

在 PostgreSQL 中执行迁移脚本（按顺序）：

```bash
psql -U postgres -d ip_factory -f db/migrations/001_init.sql
psql -U postgres -d ip_factory -f db/migrations/002_ingest_tasks.sql
```

或使用 GUI 工具依次执行上述 SQL 文件。

### 4. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>

## 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── db/                   # 数据库连接与模型
│   │   ├── session.py       # 引擎与会话
│   │   └── models.py        # SQLAlchemy 表模型
│   └── routers/
│       ├── memory.py         # Memory Agent 接口（ingest / retrieve / 打标）
│       └── config_memory.py # Memory 配置 CRUD
├── db/
│   └── migrations/
│       └── 001_init.sql     # 建表脚本
├── requirements.txt
├── .env.example
└── README.md
```

## API 概览（Phase 1）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/ip | 创建 IP |
| GET  | /api/v1/ip/{ip_id} | 查询 IP |
| POST | /api/v1/memory/ingest | 素材录入（入队列，后台处理入库） |
| GET  | /api/v1/memory/ingest/{task_id} | 录入任务状态 |
| POST | /api/v1/memory/retrieve | 语义检索 |
| GET  | /api/v1/memory/pending-labels | 待复核打标列表 |
| POST | /api/v1/memory/labels/{asset_id} | 提交打标复核 |
| GET  | /api/v1/config/memory | 读取 Memory 配置 |
| POST | /api/v1/config/memory | 保存 Memory 配置 |
| GET  | /api/v1/integrations/feishu/spaces | 列出飞书知识空间 |
| POST | /api/v1/integrations/feishu/sync | 飞书知识库同步到 IP Memory |
| GET/POST | /api/v1/integrations/baidu/config | 百度网盘 access_token 配置 |
| POST | /api/v1/integrations/baidu/sync | 百度网盘目录同步到 IP Memory |
