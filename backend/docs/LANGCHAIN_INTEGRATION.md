# LangChain 集成指南

本文档说明如何将 LangChain 框架的先进实践集成到 AI-Native IP 项目中。

## 1. LangChain 核心概念

| 概念 | 说明 | 在项目中的应用 |
|------|------|---------------|
| **LCEL** | 链式表达式语言 | 内容生成管道 |
| **Agents** | 自主决策代理 | 策略/生成Agent |
| **Memory** | 状态持久化 | IP记忆管理 |
| **RAG** | 检索增强生成 | 知识检索 |
| **Tools** | 外部能力接口 | 热点/竞品分析 |

---

## 2. 快速开始

### 安装依赖

```bash
pip install langchain langchain-core langchain-openai langchain-community
```

### 基础使用

```python
from app.services.langchain_integrator import LangChainIntegrator

# 初始化
integrator = LangChainIntegrator(
    llm=chat_model,
    vectorstore=qdrant_store
)

# 创建内容生成链
chain = integrator.create_content_chain()

# 执行
result = chain.invoke({
    "query": "关于职场成长的观点",
    "ip_style": {"tone": "幽默", "vocabulary": ["干货", "避坑"]}
})
```

---

## 3. 核心组件详解

### 3.1 LCEL 内容生成链

```python
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 完整内容生成管道
content_chain = (
    RunnableParallel(
        context=lambda x: retrieve_context(x["query"]),
        style=lambda x: get_ip_style(x["ip_id"]),
        trending=lambda x: get_trending_topics()
    )
    | build_prompt           # 构建提示词
    | llm                   # 调用LLM
    | StrOutputParser()      # 解析输出
)
```

**优势**：
- 流式输出支持
- 错误自动重试
- 并行/串行灵活组合

### 3.2 Agent 实现

```python
from langchain.agents import create_openai_functions_agent

# 策略Agent
strategy_agent = create_openai_functions_agent(
    llm=chat_model,
    tools=[search_tool, analyze_tool, score_tool],
    prompt=strategy_prompt
)

# 执行
result = strategy_agent.invoke({
    "input": "分析当前热点，推荐选题"
})
```

### 3.3 Memory 组件

```python
from langchain.memory import ConversationTokenBufferMemory
from langchain.memory.vectorstore import VectorStoreRetrieverMemory

# 短期记忆（对话上下文）
short_memory = ConversationTokenBufferMemory(
    llm=chat_model,
    max_token_limit=2000
)

# 长期记忆（IP知识库）
long_memory = VectorStoreRetrieverMemory(
    retriever=qdrant_store.as_retriever(),
    memory_key="ip_knowledge"
)
```

---

## 4. 项目集成示例

### 4.1 内容生成API

```python
from fastapi import APIRouter
from langchain_integrator import LangChainIntegrator

router = APIRouter()

@router.post("/generate/content")
async def generate_content(request: GenerateRequest):
    integrator = LangChainIntegrator(llm=chat_model)
    
    chain = integrator.create_content_chain()
    
    result = await chain.ainvoke({
        "query": request.topic,
        "ip_id": request.ip_id,
        "ip_style": get_ip_style(request.ip_id)
    })
    
    return {"content": result}
```

### 4.2 策略Agent API

```python
@router.post("/agent/strategy")
async def strategy_agent(request: StrategyRequest):
    integrator = LangChainIntegrator(llm=chat_model)
    agent = integrator.create_strategy_agent(get_langchain_tools())
    
    result = agent.invoke({
        "input": request.question,
        "ip_profile": get_ip_profile(request.ip_id)
    })
    
    return {"response": result["output"]}
```

---

## 5. LangChain vs 当前实现对比

| 功能 | 当前实现 | LangChain方式 | 优势 |
|------|---------|-------------|------|
| 检索 | 手动实现 | `RetrievalChain` | 自动RAG |
| 生成 | 散乱调用 | `LCEL链` | 可组合/可观测 |
| Agent | 自己写 | `create_agent` | 工具扩展简单 |
| 记忆 | 用量统计 | `Memory组件` | 多类型支持 |
| 流式 | 无 | `@streaming` | 实时输出 |

---

## 6. 迁移建议

### Phase 1: 保留当前 + LangChain补充

```
现状：检索 → 自己写生成
↓
添加：LangChain做生成链
```

### Phase 2: 逐步迁移

```
LangChain: Agent/生成
当前: 仅存储/检索
↓
最终: 全部用LangChain
```

---

## 7. 参考资料

- [LangChain中文文档](https://python.langchain.com/)
- [LCEL教程](https://python.langchain.com/docs/expression_language/)
- [Agent指南](https://python.langchain.com/docs/modules/agents/)
