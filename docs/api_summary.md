# API 端点汇总

## 内容创作工作流 API

### 环节1：竞品发现

#### 获取竞品视频（4维度排序）
```
GET /strategy/v4/competitor-videos
```

**参数：**
- `ip_id` (required): IP ID
- `limit` (optional): 返回数量，默认10
- `content_type` (optional): 内容类型过滤
- `sort_by` (optional): 排序维度

**返回：** 竞品视频列表（含链接）

---

### 环节2：内容提取

#### 单条提取
```
POST /strategy/v4/extract-content
```

**请求体：**
```json
{
  "url": "https://www.douyin.com/video/xxx",
  "use_cache": true
}
```

**返回：** 结构化内容（hook/body/tags等）

#### 批量提取
```
POST /strategy/v4/extract-content/batch
```

**请求体：**
```json
{
  "urls": ["url1", "url2", ...],
  "use_cache": true
}
```

#### 测试提取（GET方式）
```
GET /strategy/v4/extract-content/test?url=https://...
```

---

### 环节3：标题改写

#### 单条改写
```
POST /strategy/v3/title-rewrite
```

**请求体：**
```json
{
  "ip_id": "xiaomin",
  "original_title": "90后宝妈靠副业月入过万...",
  "original_hook": "90后宝妈靠副业月入过万",
  "original_body": "分享3个真实方法",
  "tags": ["宝妈副业"],
  "content_type": "money",
  "strategy": "structure_keep"
}
```

**返回：** 改写后的标题

#### 批量改写
```
POST /strategy/v3/title-rewrite/batch?ip_id=xiaomin&strategy=structure_keep
```

**请求体：**
```json
{
  "titles": [
    {
      "title": "标题1",
      "hook": "hook1",
      "body": "body1",
      "tags": ["标签1"],
      "content_type": "money"
    }
  ]
}
```

---

### 组合流程 API

#### 环节1 + 环节2 组合
```
GET /strategy/v4/competitor-full-pipeline
```

**参数：**
- `ip_id` (required): IP ID
- `limit` (optional): 数量
- `extract_content` (optional): 是否提取内容

**说明：** 先获取竞品视频，再提取每个视频的内容

#### 环节2 + 环节3 组合
```
POST /strategy/v3/full-pipeline
```

**参数：**
- `ip_id` (required): IP ID
- `url` (required): 视频链接
- `rewrite_strategy` (optional): 改写策略

**说明：** 从URL提取内容，然后直接改写标题

---

### 调试/测试 API

#### 测试多源热榜
```
GET /strategy/v4/multi-source-test
```

**参数：**
- `ip_id`: IP ID
- `limit`: 数量
- `use_builtin_fallback`: 是否使用内置库兜底

#### 获取内置爆款库
```
GET /strategy/v4/builtin-topics
```

**参数：**
- `ip_id`: IP ID
- `limit`: 数量

---

## 数据模型

### ExtractedContent（环节2输出）

```json
{
  "success": true,
  "url": "string",
  "platform": "douyin",
  "video_id": "string",
  "author": "string",
  "original_title": "string",
  "title_clean": "string",
  "hook": "string",
  "body": "string",
  "tags": ["string"],
  "content_type": "money|emotion|skill|life",
  "stats": {
    "play_count": 0,
    "like_count": 0,
    "share_count": 0
  }
}
```

### RewriteResult（环节3输出）

```json
{
  "success": true,
  "original": {
    "title": "string",
    "hook": "string",
    "body": "string"
  },
  "rewritten": {
    "title": "string",
    "hook": "string",
    "body": "string"
  },
  "strategy": "string",
  "ip_id": "string",
  "ip_name": "string",
  "content_type": "string"
}
```

---

## 使用示例

### 完整工作流示例

```bash
# 1. 获取竞品视频
curl "http://localhost:8000/strategy/v4/competitor-videos?ip_id=xiaomin&limit=5"

# 2. 提取单个视频内容
curl -X POST "http://localhost:8000/strategy/v4/extract-content" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.douyin.com/video/xxx"}'

# 3. 改写标题
curl -X POST "http://localhost:8000/strategy/v3/title-rewrite" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_id": "xiaomin",
    "original_title": "90后宝妈靠副业月入过万...",
    "original_hook": "90后宝妈靠副业月入过万",
    "original_body": "分享3个真实方法",
    "tags": ["宝妈副业"],
    "content_type": "money"
  }'
```

### 一键完整流程

```bash
# 从URL直接获取改写标题
curl -X POST "http://localhost:8000/strategy/v3/full-pipeline?ip_id=xiaomin&url=https://..."
```

---

## 状态码

| 状态码 | 说明 |
|-------|------|
| 200 | 成功 |
| 404 | IP不存在 |
| 422 | 参数验证失败 |
| 500 | 服务器错误 |

## 错误处理

所有API返回的数据都包含`success`字段：

```json
{
  "success": false,
  "error": "错误信息"
}
```
