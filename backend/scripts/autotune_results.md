# AutoTune 优化结果

## 1. 知识库录入优化 (ingest)
**20次实验 | 最佳得分: 2.6333**

| 参数 | 推荐值 |
|------|--------|
| CHUNK_CHUNK_SIZE | 2000 |
| CHUNK_OVERLAP | 100 |
| CHUNK_PARENT_SIZE | 5000 |
| INGEST_EMBED_BATCH_SIZE | 32 |
| INGEST_COMMIT_EVERY | 20 |

---

## 2. 检索优化 (retrieve)
**20次实验 | 最佳得分: 0.7367 (latency，越低越好)**

| 参数 | 推荐值 |
|------|--------|
| TOP_K | 10 |
| VECTOR_WEIGHT | 0.7 |
| HYBRID_MIN_SCORE | 0.2 |

---

## 3. 内容生成优化 (generation)
**20次实验 | 最佳得分: 1.0 (quality)**

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| TEMPERATURE | 0.5 | 中等创造性 |
| MAX_TOKENS | 1500 | 中等长度 |
| TOP_P | 0.9 | 核采样 |

---

## Railway 环境变量汇总

```bash
# 分块参数
CHUNK_CHUNK_SIZE=2000
CHUNK_OVERLAP=100
CHUNK_PARENT_SIZE=5000

# 录入参数
INGEST_EMBED_BATCH_SIZE=32
INGEST_COMMIT_EVERY=20

# 检索参数
TOP_K=10
VECTOR_WEIGHT=0.7
HYBRID_MIN_SCORE=0.2

# 生成参数
TEMPERATURE=0.5
MAX_TOKENS=1500
TOP_P=0.9
```
