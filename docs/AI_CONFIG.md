# AI 服务配置说明

本系统通过 OpenAI 兼容 API 提供以下能力：

- **Embedding**：文本向量化，用于语义检索
- **LLM Chat**：自动打标（IP 可配术语表；未配时使用内容语义参考维，见 `docs/TAG_TAXONOMY_REFERENCE.md`）
- **Whisper**：音视频转写（video/audio 类素材录入）

## 环境变量

| 变量 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| `OPENAI_API_KEY` | 是（启用文本 AI 时） | LLM + Embedding 的 API 密钥 | - |
| `OPENAI_BASE_URL` | 否 | 主客户端 Base URL（如 DeepSeek `https://api.deepseek.com`） | OpenAI 官方 |
| `EMBEDDING_MODEL` | 否 | Embedding 模型 | `text-embedding-3-small` |
| `LLM_MODEL` | 否 | 对话/打标模型 | `gpt-4o-mini` |
| `AUTO_TAG_ENABLED` | 否 | 是否启用录入自动打标 | `true` |
| `OPENAI_TRANSCRIPTION_API_KEY` | 否 | **仅语音转写**用密钥；不填则与 `OPENAI_API_KEY` 相同 | - |
| `OPENAI_TRANSCRIPTION_BASE_URL` | 否 | 转写端点；填了转写 Key 且本项留空时默认 `https://api.openai.com/v1` | 与主 `OPENAI_BASE_URL` 或官方 |
| `WHISPER_MODEL` | 否 | 转写模型名 | `whisper-1` |

## 接入步骤

### 本地开发

1. **密钥与数据库填在 `backend/.env`**（仓库已提供该文件模板，且已加入 `.gitignore`，勿提交）。
2. 若误删，可复制：`cp backend/.env.example backend/.env`（Windows：`copy backend\.env.example backend\.env`）。
3. 按需填写 `DATABASE_URL`、`OPENAI_*`、`OPENAI_TRANSCRIPTION_*` 等。

环境变量由 `backend/app/env_loader.py` 固定从 **`backend/.env`** 加载，与你在哪个目录执行 `uvicorn` 无关。

### 线上（Railway 等）

在平台 **Variables** 中配置同名变量，无需上传 `.env` 文件。

## 行为说明

- **未配置 `OPENAI_API_KEY`**：所有 AI 调用静默跳过，不报错
- **自动打标（支持 IP 术语表）**：素材录入时，每个分块会调用 LLM 生成标签，写入 `asset_meta.auto_labels`
  - 若该 IP 配置了 `tag_config.tag_categories`，模型会严格按术语表候选值打标（由运营可配）
  - 若未配置术语表，会回退到**内容语义参考维**（`theme_domain` / `emotion_anchor` / `narrative_structure` / `persona_mode`，候选值见 `docs/TAG_TAXONOMY_REFERENCE.md`，**仅供参考**，建议按 IP 落库配置）
- **Whisper 转写**：`source_type` 为 `video` 或 `audio` 且 `source_url` 存在时，会下载文件并调用 Whisper 转写后作为 `content`
- **失败处理**：打标或转写失败不阻塞录入，会写入占位内容或跳过 auto_labels

## 术语表配置建议（运营）

在 IP 配置中的 `tag_config.tag_categories` 维护术语表，每个分类需包含：

- `name`：分类显示名（如「情绪」）
- `type`：字段 key（如 `emotion`，将写入 `auto_labels`）
- `values[].value`：实际标签值（模型只会从这里选择）
- `values[].enabled`：可选，`false` 时该值不参与自动打标

**参考术语表（可整段复制再按 IP 改）**：`docs/TAG_TAXONOMY_REFERENCE.md`。

## 国内/代理部署示例

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://your-proxy.example.com/v1
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o-mini
```

## DeepSeek（LLM + Embedding）+ OpenAI（Whisper）拆分示例

主密钥指向 DeepSeek；转写单独使用 OpenAI 官方 Key（DeepSeek 无 Whisper）：

```bash
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com
EMBEDDING_MODEL=deepseek-embedding
LLM_MODEL=deepseek-chat

OPENAI_TRANSCRIPTION_API_KEY=sk-your-openai-key
# 可不写，已自动默认官方 https://api.openai.com/v1
```

## 相关代码

- `backend/app/config/ai_config.py`：配置读取
- `backend/app/services/ai_client.py`：embed、chat、transcribe、suggest_tags_for_content
- `backend/app/services/ingest_service.py`：录入流水线中调用自动打标与 Whisper
