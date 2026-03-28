# AutoTune Program - 参数优化策略

## 目标
自动优化 AI-Native IP 项目的运行时参数，提升知识库录入和检索效果。

## 优化目标

### 1. 知识库录入 (ingest)
**指标**: 吞吐量 + 质量平衡

**可调参数**:
- `CHUNK_SIZE`: 分块大小 (500-2000)
- `CHUNK_OVERLAP`: 块重叠 (50-200)
- `INGEST_EMBED_BATCH_SIZE`: 向量批量大小 (4-32)
- `INGEST_COMMIT_EVERY`: 提交频率 (10-50)

**评估方式**: 
- 处理速度 (chunks/second)
- 内存峰值
- 向量完整性

### 2. 检索 (retrieve)
**指标**: 召回率 + 延迟

**可调参数**:
- `TOP_K`: 返回结果数 (3-20)
- `VECTOR_WEIGHT`: 向量权重 (0.3-0.8)
- `HYBRID_MIN_SCORE`: 最小分数阈值 (0.1-0.5)

**评估方式**:
- 召回率 (相关结果占比)
- 响应延迟 (ms)
- 综合得分

### 3. 内容生成 (generation)
**指标**: 质量 / 延迟

**可调参数**:
- `TEMPERATURE`: 创造性 (0.1-0.9)
- `MAX_TOKENS`: 最大长度 (500-2000)
- `TOP_P`: 核采样 (0.8-1.0)

**评估方式**:
- 生成质量 (人工/自动评估)
- 生成延迟

## 优化策略

### 策略1: 随机搜索 (Random Search)
每次随机选择一组参数运行测试。

### 策略2: 网格搜索 (Grid Search)
遍历参数空间的所有组合。

### 策略3: 贝叶斯优化 (Bayesian)
使用高斯过程建模，智能选择下一个测试点。

## 运行方式

```bash
# 优化知识库录入参数，5分钟
python scripts/autotune.py --target ingest --metric recall --time 300

# 优化检索参数，10分钟
python scripts/autotune.py --target retrieve --metric latency --time 600

# 优化生成参数，最多20次实验
python scripts/autotune.py --target generation --metric quality --max 20
```

## 输出

- 最佳参数保存到: `data/autotune/best_params.json`
- 每个实验记录: `data/autotune/exp_*.json`

## 扩展

要添加新的优化目标：
1. 在 `autotune.py` 中添加参数空间定义
2. 实现对应的 `_evaluate_xxx` 方法
3. 在 `program.md` 中描述新目标
