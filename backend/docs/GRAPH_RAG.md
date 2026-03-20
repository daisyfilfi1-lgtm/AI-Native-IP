# Graph RAG 知识图谱配置指南

本文档说明如何配置 Neo4j 知识图谱，实现基于图关系的语义检索。

## 什么是 Graph RAG？

| 检索方式 | 原理 | 适用场景 |
|---------|------|---------|
| **向量检索** | 语义相似度 | 概念理解、主题匹配 |
| **关键词检索** | 精确匹配 | 实体查找 |
| **Graph RAG** | 知识图谱关系推理 | 关联分析、多跳推理 |

**Graph RAG 优势**：
- 理解实体之间的关系
- 支持多跳推理（如：A→B→C）
- 可解释性强（可追溯关系路径）

## 1. 安装 Neo4j

### 方式A：Docker（推荐）

```bash
# 启动 Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j

# 访问 http://localhost:7474
```

### 方式B：Neo4j Aura（云端）

1. 注册 [Neo4j Aura](https://neo4j.com/cloud/aura/)
2. 创建 Free Tier 数据库
3. 获取连接凭据

## 2. 配置环境变量

```bash
# Neo4j 连接
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

## 3. API 接口

### 构建知识图谱

```bash
POST /api/v1/graph/build
Content-Type: application/json

{
  "ip_id": "test_001",
  "force_rebuild": false  // 是否强制重建
}
```

**响应**：
```json
{
  "entities": 45,
  "relations": 32,
  "errors": []
}
```

### 图检索

```bash
POST /api/v1/graph/retrieve
Content-Type: application/json

{
  "ip_id": "test_001",
  "query": "用户体验",
  "depth": 2,
  "limit": 20
}
```

**响应**：
```json
{
  "seed_nodes": [
    {"name": "用户", "type": "PERSON", "description": "产品的使用者"}
  ],
  "paths": [
    {
      "from": "用户",
      "relation": "HAS_NEED",
      "to": "体验",
      "context": "用户需要良好的产品体验"
    }
  ]
}
```

### 获取图谱统计

```bash
GET /api/v1/graph/stats/test_001
```

**响应**：
```json
{
  "nodes": {"PERSON": 10, "CONCEPT": 25, "ORGANIZATION": 5},
  "relations": {"RELATED_TO": 20, "HAS_NEED": 15},
  "total_nodes": 40,
  "total_relations": 35
}
```

### 删除图谱

```bash
DELETE /api/v1/graph/test_001
```

## 4. 工作原理

### 实体提取

```
文本内容 → LLM提取 → 实体+关系 → Neo4j存储
```

示例输入：
> "张三是腾讯的产品经理，负责微信的用户体验优化。"

LLM 提取结果：
```json
[
  {"type": "PERSON", "name": "张三", "properties": {"role": "产品经理", "company": "腾讯"}},
  {"type": "ORGANIZATION", "name": "腾讯"},
  {"type": "PRODUCT", "name": "微信"},
  {"type": "CONCEPT", "name": "用户体验"},
  {"type": "RELATION", "from": "张三", "to": "腾讯", "relation": "WORKS_AT"},
  {"type": "RELATION", "from": "张三", "to": "微信", "relation": "RESPONSIBLE_FOR"},
  {"type": "RELATION", "from": "微信", "to": "用户体验", "relation": "OPTIMIZES"}
]
```

### 图检索流程

```
Query: "微信的负责人是谁？"

1. 找到包含"微信"的实体
2. 扩展该实体的邻居关系
3. 沿着 WORKS_AT / RESPONSIBLE_FOR 关系追溯
4. 返回：张三
```

## 5. 混合检索建议

生产环境推荐**向量 + 图谱混合检索**：

```python
# 1. 向量检索（语义理解）
vec_results = vector_search("用户体验", top_k=10)

# 2. 图谱检索（关系推理）
graph_results = graph_retrieve("用户体验", depth=2)

# 3. 结果融合
combined = merge_results(vec_results, graph_results, weights=[0.6, 0.4])
```

## 6. 可视化

访问 Neo4j Browser：`http://localhost:7474`

```cypher
# 查看某个IP的图谱
MATCH (n {ip_id: 'test_001'})-[:RELATED_TO]->(m)
RETURN n, m
LIMIT 50
```

## 故障排除

### 连接失败

```bash
# 检查 Neo4j 是否运行
curl http://localhost:7474

# 测试连接
cypher-shell -u neo4j -p your_password "MATCH (n) RETURN count(n)"
```

### 实体未创建

1. 检查 LLM 是否正常工作
2. 检查日志中的实体提取错误
3. 确认文本内容足够长（>50字符）
