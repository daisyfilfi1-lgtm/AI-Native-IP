# AI 服务性价比替代方案

针对「IP 素材录入 → 自动打标 → 语义检索 → 音视频转写」的业务链路，结合 2025 年主流模型能力与定价，提供以下替代 OpenAI 的方案。

---

## 一、业务能力拆解

| 能力 | 用途 | 调用频率 | 当前依赖 |
|------|------|----------|----------|
| **LLM Chat** | 自动打标 emotion/scene/cognitive | 每分块 1 次 | GPT-4o-mini |
| **Embedding** | 向量化 → 语义检索 | 每素材 1 次 | text-embedding-3-small |
| **语音转写** | video/audio → 文本 | 按需 | Whisper API |

---

## 二、LLM + Embedding 替代方案

### 1. DeepSeek（推荐：海外 / 代理可访问场景）

| 项目 | 说明 |
|------|------|
| **API 兼容** | 完全兼容 OpenAI 接口，仅改 `base_url` 和 `model` |
| **LLM 价格** | deepseek-chat：约 $0.28/1.1 每百万 token（输入/输出），约为 GPT-4o-mini 的 1/5 |
| **Embedding** | deepseek-embedding：约 $0.05/百万 token，768 维，极低成本 |
| **配置** | `OPENAI_BASE_URL=https://api.deepseek.com`，`LLM_MODEL=deepseek-chat`，`EMBEDDING_MODEL=deepseek-embeddingding` |

**优势**：价格最低，能力接近 GPT-4，代码改动 minimal  
**注意**：无内置 Whisper，语音转写需单独接入；Embedding 为 768 维（OpenAI 为 1536 维），切换时需重建向量索引

---

### 2. 阿里云通义千问（推荐：国内、合规优先）

| 项目 | 说明 |
|------|------|
| **LLM 价格** | qwen-turbo 约 0.0003/0.0006 元/千 token，100 万 token 免费额度 |
| **Embedding** | text-embedding-v3，支持 OpenAI 兼容接入 |
| **免费额度** | 新用户千万级 token 免费，单模型 100 万 token 限免 |

**优势**：国内直连、合规、中文效果好，成本低  
**接入方式**：通过 One API / 代理 转为 OpenAI 格式，或直接调通义 API（需适配 `ai_client`）

---

### 3. Google Gemini（适合：有免费额度、海外）

| 项目 | 说明 |
|------|------|
| **LLM 价格** | Gemini 2.5 Flash-Lite 约 $0.10/0.40 每百万 token |
| **免费额度** | 有免费 tier，适合试跑和轻量场景 |
| **Embedding** | 提供 text-embedding 类模型 |

**优势**：免费额度友好，多模型可选  
**注意**：国内需代理，API 格式与 OpenAI 不完全一致，需封装适配层

---

### 4. 智谱 GLM / 百川（国内备选）

| 项目 | 说明 |
|------|------|
| **智谱 GLM-4** | 约 0.1/0.2 元/千 token，语义理解稳定 |
| **百川** | 价格相近，适合需要多供应商的国内场景 |

---

## 三、语音转写替代方案

| 方案 | 价格 | 适用场景 |
|------|------|----------|
| **OpenAI Whisper** | $0.006/分钟 | 海外、追求效果 |
| **阿里云录音识别** | 0.33 元/小时 ≈ 0.0055 元/分钟 | 国内、合规 |
| **阿里云闲时版** | 0.45 元/小时起 | 非实时、批量处理 |
| **腾讯云** | 资源包（如 60 小时/年） | 用量稳定、预付费 |
| **Faster-Whisper 本地** | 完全免费 | 有 GPU/CPU 算力、对隐私敏感 |

**Faster-Whisper**：开源、本地部署，支持中文。适合有自建服务器且希望零云成本的场景，需在 ingest 流水线中接入本地转写服务或 HTTP 接口。

---

## 四、推荐组合方案

### 方案 A：DeepSeek 全家桶 + Whisper（海外/代理）

```
LLM/Embedding: DeepSeek（base_url + model 切换）
语音转写: OpenAI Whisper（$0.006/分钟，或通过代理）
```

- **成本**：LLM/Embedding 约为纯 OpenAI 的 1/5–1/3  
- **实现**：改环境变量即可，无需改代码

---

### 方案 B：通义千问 + 阿里云 STT（国内首选）

```
LLM/Embedding: 通义千问（通过 One API 或代理转 OpenAI 格式）
语音转写: 阿里云录音文件识别（0.33 元/小时）
```

- **成本**：国内计费，合规性好  
- **实现**：LLM 需 One API 等中转；STT 需在 `ai_client` 中增加阿里云调用分支

---

### 方案 C：混合 + 本地 Whisper（成本最优）

```
LLM/Embedding: DeepSeek 或 通义
语音转写: Faster-Whisper 本地部署（HTTP 服务）
```

- **成本**：转写无云费用，LLM 按所选厂商计费  
- **实现**：需部署 Faster-Whisper 服务，并在 `transcribe` 中增加本地服务调用

---

## 五、DeepSeek 快速接入（零代码改动）

在 `.env` 或 Railway Variables 中配置：

```bash
# 使用 DeepSeek 替代 OpenAI（LLM + Embedding）
OPENAI_API_KEY=sk-your-deepseek-api-key
OPENAI_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
EMBEDDING_MODEL=deepseek-embedding
```

当前 `ai_client` 已支持 `base_url` 与 `model` 配置，上述配置即可生效。

**LLM + Embedding 用 DeepSeek、语音转写用 OpenAI**：再增加转写专用密钥（自动走官方 `https://api.openai.com/v1`）：

```bash
OPENAI_TRANSCRIPTION_API_KEY=sk-your-openai-key
```

详见 `docs/AI_CONFIG.md`。

---

## 六、后续扩展建议

1. **多 Provider 抽象**：在 `ai_config` 中增加 `AI_PROVIDER=openai|deepseek|qwen`，按 provider 选择 base_url 和 model 默认值  
2. **STT 可插拔**：将 `transcribe` 抽象为接口，支持 Whisper / 阿里云 / 本地 Faster-Whisper 等实现  
3. **用量与成本监控**：记录 token 消耗和转写时长，便于对比不同方案的业务成本  
