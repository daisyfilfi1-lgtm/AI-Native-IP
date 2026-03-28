# Qdrant 向量数据库配置指南

本文档说明如何配置 Qdrant 向量库以提升 AI-Native IP 的检索性能。

## 为什么需要 Qdrant？

| 对比项 | PostgreSQL JSONB | Qdrant |
|--------|-----------------|--------|
| 向量维度 | 受限 | 支持任意维度 |
| 检索算法 | 基础余弦相似度 | HNSW + 量化 |
| 混合搜索 | 不支持 | 向量 + 关键词 |
| 性能 | O(n) 全表扫描 | O(log n) 索引 |
| 吞吐量 | ~100 QPS | ~10000+ QPS |

## 1. 安装 Qdrant

### 方式A：Docker（推荐本地开发）

```bash
# 启动 Qdrant
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  qdrant/qdrant

# 验证
curl http://localhost:6333/collections
```

### 方式B：Qdrant Cloud（生产环境）

1. 注册 [Qdrant Cloud](https://cloud.qdrant.io/)
2. 创建 Cluster
3. 获取 URL 和 API Key

## 2. 配置环境变量

```bash
# 本地模式
QDRANT_URL=http://localhost:6333

# 云端模式
QDRANT_URL=https://xxxxx.qdrant.cloud
QDRANT_API_KEY=your_api_key
```

## 3. API 接口

### 向量检索

```bash
POST /api/v1/vector/search
Content-Type: application/json

{
  "ip_id": "test_001",
  "query": "关于IP的价值观",
  "top_k": 10,
  "use_hybrid": true
}
```

### 获取 Collection 信息

```bash
GET /api/v1/vector/collection/{ip_id}
```

### 删除向量

```bash
DELETE /api/v1/vector/collection/{ip_id}  # 危险：删除整个collection
DELETE /api/v1/vector/asset/{asset_id}?ip_id={ip_id}  # 删除单个
```

## 4. 数据迁移

### 迁移现有数据

```bash
# 预览迁移数量
python scripts/migrate_to_qdrant.py --dry-run

# 执行迁移
python scripts/migrate_to_qdrant.py

# 迁移指定IP
python scripts/migrate_to_qdrant.py --ip-id test_001
```

### 迁移过程

1. 从 PostgreSQL `asset_vectors` 表读取现有向量
2. 创建 Qdrant Collection（每个IP一个）
3. 批量写入向量和payload
4. 保持PostgreSQL同步（向后兼容）

## 5. 混合搜索

Qdrant 支持**向量相似度 + 关键词**混合搜索：

```python
# 向量搜索：语义理解
results = client.search(
    query_vector=embed("用户体验设计"),
    limit=10,
)

# 混合搜索：语义 + 关键词
results = client.search(
    query_vector=embed("用户体验设计"),
    query_text="用户体验设计",  # 关键词补充
    limit=10,
)
```

**混合搜索优势**：
- 向量捕获语义相似
- 关键词确保精确匹配
- 相互补充，提升召回率

## 6. 性能调优

### HNSW 参数

```python
search_params = SearchParams(
    hnsw_ef=128,      # 搜索时探索的候选数，越高越准确但越慢
    exact=False,       # False=HNSW近似，True=精确但慢
)
```

### 量化（生产环境）

```python
# 启用量化以减少内存
client.update_collection(
    collection_name="ip_xxx",
    vectors_config={
        "text": {
            "quantization": "int8",  # 8位量化，内存减少4倍
        }
    }
)
```

## 7. 监控

```bash
# Qdrant Dashboard
http://localhost:6333/dashboard

# 集群健康
curl http://localhost:6333/health
```

## 故障排除

### 连接失败

```bash
# 检查 Qdrant 是否运行
curl http://localhost:6333/collections

# 检查网络
ping localhost -4
```

### 维度不匹配

```
Error: vector size mismatch
```

**解决**：确保 embedding 模型与 collection 维度一致：
- `text-embedding-3-small`: 1536维
- `text-embedding-3-large`: 3072维
- `deepseek-embedding`: 1536维
