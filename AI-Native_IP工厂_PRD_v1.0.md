# AI-Native IP工厂产品需求文档（PRD）v1.0

## 一、项目概述

### 1.1 背景
传统IP内容生产依赖人工创意，产能受限（人均2条/天），存在风格不一致、合规风险高、数据复盘滞后等问题。

### 1.2 目标
- 产能目标：单IP日产出300条（B级），人工审核<1小时
- 质量目标：AI生成与IP过往爆款风格相似度>85%，过审率>95%
- 效率目标：选题到成片<2小时

### 1.3 范围
In Scope：文案生成、数字人视频、数据复盘、选题决策  
Out of Scope：真人实拍（A级）、私域运营

---

## 二、系统架构

### 2.1 总体架构
主控Orchestrator + 6个专业Agent + 数据层 + 外部服务

### 2.2 Agent定义

#### Agent 1: IP记忆Agent（Memory Agent）
**职责**：构建IP实时数字孪生  
**输入**：音视频/文本/实时对话  
**输出**：结构化向量知识库 + 实时检索API

**技术栈**：
- ASR: Whisper API
- Embedding: text-embedding-3-large
- Storage: Pinecone + Neo4j

**核心接口**：
```
POST /api/v1/memory/ingest
POST /api/v1/memory/retrieve
```

#### Agent 2: 策略Agent（Strategy Agent）
**职责**：决策"做什么内容"和"怎么投放"  
**输入**：平台热点数据 + 历史表现 + IP日程  
**输出**：每日选题队列（已评分）+ 投放策略

**核心功能**：
- 竞品数据抓取（RPA）
- 四维评分算法
- 预测性选题（LSTM）

#### Agent 3: 内容重组Agent（Remix Agent）
**职责**：竞品解构并IP化重组  
**输入**：竞品视频URL + IP素材库  
**输出**：3个重组版本（不同情绪）

**工作流程**：
1. 解构竞品结构（Hook/Setup/Conflict/Climax/CTA）
2. RAG检索IP相关素材
3. 观点升维（经验→规律）
4. 去重检测（<25%）

#### Agent 4: 文案生成Agent（Generation Agent）
**职责**：转化为符合IP风格的终稿  
**输入**：重组内容 + 风格模型  
**输出**：终稿文案（带标记）

**双模型架构**：
- Base Model: Fine-tuned Claude 3 Haiku（风格模仿）
- 实时强化：RAG动态注入最新素材

**关键功能**：
- 情绪工程（W型曲线）
- 去AI化（口语瑕疵）
- 变现植入

#### Agent 5: 合规Agent（Compliance Agent）
**职责**：工业刹车系统  
**输入**：生成文案  
**输出**：绿灯/黄灯/红灯 + 修正建议

**三级审查**：
1. 平台合规（敏感词/导流违规）
2. 广告法合规（绝对化用语）
3. 原创合规（查重<25%）

#### Agent 6: 视觉Agent（Visual Agent）
**职责**：文案转视觉方案  
**输入**：文案 + 情绪曲线  
**输出**：分镜脚本 / 数字人视频

**子模块**：
- 分镜自动生成
- 数字人拍摄（HeyGen API）
- 场景推荐

#### Agent 7: 分析Agent（Analytics Agent）
**职责**：自动化数据归因与策略迭代  
**输入**：平台数据  
**输出**：归因分析 + 自动周报

**反馈闭环**：
- 爆款特征 → 更新策略Agent
- 失败归因 → 更新重组Agent

### 2.3 数据层
- 向量库：Pinecone（资产存储）
- 图数据库：Neo4j（关系推理）
- 关系库：PostgreSQL（业务数据）
- 对象存储：S3（视频/图片）

---

## 三、核心数据模型

### 3.1 IP资产模型
```python
class IPAsset:
    asset_id: str
    ip_id: str
    asset_type: story|opinion|joke|data
    content: str
    content_vector: List[float]
    metadata: {
        emotion_tags, scene_tags, cognitive_tags,
        product_relevance, usage_count, core_asset
    }
    relations: List[{type, target}]
```

### 3.2 内容草稿模型
```python
class ContentDraft:
    draft_id: str
    ip_id: str
    level: A|B|C
    workflow: {
        source_topic_id, competitor_urls,
        remix_version, generation_model, assets_used
    }
    quality_score: {
        originality, ip_similarity,
        emotion_curve, predicted_completion
    }
    compliance_status: pending|passed|failed|warning
```

---

## 四、接口设计

### 4.1 Orchestrator接口

**启动工作流**
```
POST /api/v1/orchestrator/start
Request: {
    workflow_type: daily_content,
    ip_id: zhangkai_001,
    content_level: B,
    priority: normal
}
Response: {
    task_id: task_001,
    status: PROCESSING,
    websocket_url: ws://.../task_001
}
```

**查询任务状态**
```
GET /api/v1/orchestrator/task/{task_id}/status
```

### 4.2 Memory Agent接口

**资产录入**
```
POST /api/v1/memory/ingest
Request: {
    ip_id: zhangkai_001,
    source_type: video,
    url: https://.../interview.mp4
}
```

**语义检索**
```
POST /api/v1/memory/retrieve
Request: {
    ip_id: zhangkai_001,
    query: 深夜崩溃但最终翻盘的故事,
    filters: {emotion_tags: [despair, hope], usage_limit: 3}
}
```

### 4.3 Generation Agent接口

**生成文案**
```
POST /api/v1/generation/draft
Request: {
    remix_version_id: remix_v1_anger,
    ip_id: zhangkai_001,
    content_level: B,
    style_strength: 0.8
}
Response: {
    draft_id: draft_0317_01,
    full_script: 完整口播文案,
    emotion_curve: [...],
    assets_cited: [story_001, opinion_003]
}
```

---

## 五、非功能需求

### 5.1 性能
- 并发：50个工作流同时执行
- 响应延迟：选题推荐<500ms，文案生成<30s
- 数字人视频：异步2小时内完成

### 5.2 安全
- 多IP数据物理隔离
- API Key使用AWS Secrets Manager
- 所有生成内容保留溯源链

### 5.3 可用性
- 服务等级：99.5%
- 降级策略：Claude故障时切GPT-4，HeyGen故障时转真人拍摄提醒

---

## 六、实施路线图

### Phase 1: 基建期（Week 1-3）投入：2人月
**目标**：跑通单条MVP闭环

**任务**：
- 搭建FastAPI + Celery
- 实现Memory Agent（Whisper + Pinecone）
- 实现Generation Agent（基础Prompt工程）
- 实现Compliance Agent（基础敏感词）

**验证**：生成1条文案<5分钟，原创度>70%

### Phase 2: 产能期（Week 4-8）投入：3人月
**目标**：日更100条，人效提升10倍

**任务**：
- Strategy Agent（竞品抓取 + 自动评分）
- Remix Agent（解构 + 杂交）
- Fine-tune风格模型
- Visual Agent（HeyGen对接）

**验证**：日产能100条，人审时间<2小时/日

### Phase 3: 智能期（Week 9-16）投入：4人月
**目标**：自迭代系统

**任务**：
- Analytics Agent（归因 + 周报）
- 知识图谱（Neo4j）
- 预测性选题（LSTM）
- 多平台适配

---

## 七、成本效益

| 成本项 | 传统团队（月） | AI-Native（月） | 节省比例 |
|--------|--------------|----------------|---------|
| 人力成本 | 60,000（6人） | 15,000（2人） | 75% |
| 拍摄成本 | 20,000 | 2,000（API） | 90% |
| 内容产能 | 60条/月 | 300条/月 | 5倍 |
| 单条成本 | 1,333元 | 57元 | 96% |

ROI：从1:3提升至1:12

---

## 八、风险提示

1. **模型幻觉**：强制RAG检索，素材必须带source_id
2. **平台限流**：保留真人内容占比>30%
3. **合规风险**：结构借鉴+原创案例，案例100%来自IP独家
4. **信任崩塌**：明确标识AI辅助创作，或确保AI质量>真人平均

---

**文档状态**：Ready for Development  
**技术负责人**：待指派  
**产品经理**：AI产品架构师
