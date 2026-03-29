# 完整工作流：3个环节

## 概述

基于竞品爆款的内容创作工作流，分为3个环节：

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  环节1:     │ →  │  环节2:     │ →  │  环节3:     │
│  竞品发现   │    │  内容提取   │    │  标题改写   │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 环节1：竞品发现（已完成）

**输入**：IP ID  
**输出**：竞品视频列表（含链接）

```
GET /strategy/v4/competitor-videos?ip_id=xiaomin&limit=10
```

**核心功能**：
- 从17个竞品账号同步视频
- 4维度排序（相关性/热度/竞争度/变现度）
- 内容类型矩阵（4-3-2-1分布）

**返回示例**：
```json
{
  "ip_id": "xiaomin",
  "total": 84,
  "videos": [
    {
      "video_id": "7485364727352478986",
      "url": "https://www.douyin.com/video/...",
      "author_name": "淘淘子",
      "original_title": "敬自已！与世界交手的第29年！",
      "like_count": 29400,
      "content_type": "emotion",
      "four_dim_score": { "relevance": 0.85, "hotness": 0.72, ... }
    }
  ]
}
```

## 环节2：内容提取（已完成）

**输入**：视频URL  
**输出**：结构化内容（标题拆分）

```
POST /strategy/v4/extract-content
```

**核心功能**：
- 调用TIKHub API获取视频详情
- 提取标题+标签
- 拆分为 hook + body

**返回示例**：
```json
{
  "success": true,
  "url": "https://www.douyin.com/video/...",
  "original_title": "90后宝妈靠副业月入过万...#宝妈副业",
  "title_clean": "90后宝妈靠副业月入过万...",
  "hook": "90后宝妈靠副业月入过万",
  "body": "分享3个真实方法",
  "tags": ["宝妈副业", "赚钱技巧"],
  "content_type": "money",
  "stats": { "play_count": 150000, "like_count": 8500 }
}
```

## 环节3：标题改写（已完成）

**输入**：爆款标题 + IP ID  
**输出**：IP化改写标题

```
POST /strategy/v3/title-rewrite
```

**核心功能**：
- 保留爆款结构（数字/身份/对比等）
- 替换为IP视角和内容
- AI改写 + 规则降级

**返回示例**：
```json
{
  "success": true,
  "original": {
    "title": "90后宝妈靠副业月入过万，分享3个真实方法",
    "hook": "90后宝妈靠副业月入过万",
    "body": "分享3个真实方法"
  },
  "rewritten": {
    "title": "90后UI设计师靠AI副业月入3万，分享我的3个接单渠道",
    "hook": "90后UI设计师靠AI副业月入3万",
    "body": "分享我的3个接单渠道"
  },
  "strategy": "structure_keep"
}
```

## 完整流程API

### 方式1：分步调用（推荐）

```python
import asyncio

async def full_workflow():
    # 环节1：获取竞品视频
    videos = await get_competitor_videos(ip_id="xiaomin", limit=5)
    
    results = []
    for video in videos:
        # 环节2：提取内容
        extracted = await extract_content(video["url"])
        
        if extracted["success"]:
            # 环节3：改写标题
            rewrite = await rewrite_title(
                ip_id="xiaomin",
                original_title=extracted["original_title"],
                original_hook=extracted["hook"],
                original_body=extracted["body"],
                tags=extracted["tags"],
                content_type=extracted["content_type"]
            )
            
            results.append({
                "source": video,
                "extracted": extracted,
                "rewritten": rewrite
            })
    
    return results
```

### 方式2：使用组合API

```
GET /strategy/v4/competitor-full-pipeline?ip_id=xiaomin&limit=5
```
环节1 + 环节2组合

```
POST /strategy/v3/full-pipeline?ip_id=xiaomin&url=...
```
环节2 + 环节3组合

## 数据流示例

### 完整示例：从竞品到改写标题

```
输入: IP ID = "xiaomin" (UI设计师)

环节1: 获取竞品
  ↓
发现: 淘淘子视频 "90后宝妈靠副业月入过万..."
  ↓
环节2: 提取内容
  ↓
{
  "hook": "90后宝妈靠副业月入过万",
  "body": "分享3个真实方法",
  "tags": ["宝妈副业"],
  "content_type": "money"
}
  ↓
环节3: 改写标题
  ↓
{
  "hook": "90后UI设计师靠AI副业月入3万",
  "body": "分享我的3个接单渠道"
}
  ↓
输出: "90后UI设计师靠AI副业月入3万，分享我的3个接单渠道"
```

## 技术架构

### 数据模型

```python
# 环节1 → 环节2
CompetitorVideo ──extract()──> ExtractedContent

# 环节2 → 环节3  
ExtractedContent ──rewrite()──> RewriteResult
```

### 服务依赖

```
CompetitorSyncService
    ↓ (读取)
CompetitorVideo (DB)
    ↓ (提供URL)
SmartContentExtractor
    ↓ (调用)
TIKHub API
    ↓ (返回)
ExtractedContent
    ↓ (输入)
TitleRewriteService
    ↓ (调用)
AI Client / Rule Engine
    ↓ (返回)
RewriteResult
```

## 错误处理

| 环节 | 可能错误 | 处理策略 |
|-----|---------|---------|
| 环节1 | 无竞品数据 | 返回空列表，提示添加竞品账号 |
| 环节2 | TIKHub API失败 | 从DB读取已缓存数据 |
| 环节3 | AI服务失败 | 降级到规则改写 |

## 性能优化

- **缓存**: 环节2使用1小时缓存
- **并发**: 环节2批量提取限制3并发
- **降级**: 每个环节都有降级方案

## API列表

### 环节1 API
- `GET /strategy/v4/competitor-videos` - 获取竞品视频
- `GET /strategy/v4/competitor-full-pipeline` - 环节1+2组合

### 环节2 API
- `POST /strategy/v4/extract-content` - 单条提取
- `POST /strategy/v4/extract-content/batch` - 批量提取
- `GET /strategy/v4/extract-content/test` - 测试提取

### 环节3 API
- `POST /strategy/v3/title-rewrite` - 单条改写
- `POST /strategy/v3/title-rewrite/batch` - 批量改写
- `POST /strategy/v3/full-pipeline` - 环节2+3组合
