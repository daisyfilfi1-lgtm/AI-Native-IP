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

## 使用方法
把这些参数复制到 Railway 环境变量中（所有服务共享）。
