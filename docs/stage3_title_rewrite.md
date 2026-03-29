# 环节3：爆款标题 + IP → 改写标题

## 概述

基于环节2提取的爆款标题结构，结合IP人设生成改写标题。
核心原则：**保留爆款结构，替换为IP视角和内容**。

## 数据流

```
环节2输出 (ExtractedContent)
    ├── original_title: 原始标题
    ├── hook: 钩子（前半句）
    ├── body: 正文（后半句）
    ├── tags: 标签
    └── content_type: 内容类型
            ↓
    IP人设信息
    ├── name: IP名称
    ├── expertise: 擅长领域
    ├── content_direction: 内容方向
    ├── target_audience: 目标受众
    └── style_profile: 风格画像
            ↓
环节3 (TitleRewriteService)
    ├── AI改写 (首选)
    └── 规则改写 (降级)
            ↓
改写结果 (RewriteResult)
    ├── rewritten_title: 改写后标题
    ├── rewritten_hook: 改写后hook
    ├── rewritten_body: 改写后body
    └── strategy: 改写策略
```

## API端点

### 1. 单条标题改写
```
POST /strategy/v3/title-rewrite
```

**请求参数：**
```json
{
  "ip_id": "xiaomin",
  "original_title": "90后宝妈靠副业月入过万，分享3个真实方法",
  "original_hook": "90后宝妈靠副业月入过万",
  "original_body": "分享3个真实方法",
  "tags": ["宝妈副业", "赚钱技巧"],
  "content_type": "money",
  "strategy": "structure_keep"
}
```

**响应：**
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
  "strategy": "structure_keep",
  "ip_id": "xiaomin",
  "ip_name": "小敏设计师",
  "content_type": "money"
}
```

### 2. 批量标题改写
```
POST /strategy/v3/title-rewrite/batch?ip_id=xiaomin&strategy=structure_keep
```

**请求参数：**
```json
{
  "titles": [
    {
      "title": "标题1",
      "hook": "hook1",
      "body": "body1",
      "tags": ["标签1"],
      "content_type": "money"
    },
    ...
  ]
}
```

### 3. 完整流程（提取+改写）
```
POST /strategy/v3/full-pipeline?ip_id=xiaomin&url=https://...&rewrite_strategy=structure_keep
```

一站式完成环节2（提取）+ 环节3（改写）。

## 改写策略

| 策略 | 说明 | 适用场景 |
|-----|------|---------|
| `structure_keep` | 保留爆款结构，替换为IP视角 | 默认策略 |
| `emotion_shift` | 转换情绪角度 | 如从焦虑转为希望 |
| `angle_flip` | 反转观点角度 | 如从避坑转为推荐 |

## 核心实现

### TitleRewriteService

```python
class TitleRewriteService:
    async def rewrite(
        self,
        ip_id: str,
        original_title: str,
        original_hook: str,
        original_body: str,
        tags: List[str],
        content_type: str,
        strategy: str = "structure_keep"
    ) -> RewriteResult:
        # 1. 获取IP人设
        ip_profile = self._extract_ip_profile(ip)
        
        # 2. 构建AI Prompt
        prompt = self._build_rewrite_prompt(...)
        
        # 3. 调用AI改写
        response = await ai_client.complete(prompt)
        
        # 4. 解析结果
        return RewriteResult(...)
```

### 规则改写（降级方案）

当AI服务不可用时，使用规则改写：

1. **身份替换**：将"宝妈"、"打工人"替换为IP的专业领域
2. **视角转换**：在hook中添加IP昵称或专业身份
3. **内容适配**：在body中加入IP的内容方向

示例：
- 原始："90后宝妈靠副业月入过万，分享3个真实方法"
- 改写："90后UI设计师靠AI副业月入3万，分享我的3个接单渠道"

## 集成方式

### 方式1：独立调用（推荐）
```python
# 环节2：提取
extracted = await extract_content_for_remix(url)

# 环节3：改写
rewrite_result = await rewrite_title(
    ip_id="xiaomin",
    original_title=extracted["original_title"],
    original_hook=extracted["hook"],
    ...
)
```

### 方式2：使用完整流程API
```python
# 一键完成提取+改写
result = await full_pipeline_api(
    ip_id="xiaomin",
    url="https://...",
    rewrite_strategy="structure_keep"
)
```

## 实现文件

- **服务**: `backend/app/services/title_rewrite_service.py`
- **API路由**: `backend/app/routers/topic_recommendation_v4.py`
- **数据模型**: `RewriteResult` (dataclass)

## 与环节2的集成

```python
# 完整流程示例
from app.services.smart_content_extractor import extract_content_for_remix
from app.services.title_rewrite_service import rewrite_title

# 环节2：从URL提取内容
extracted = await extract_content_for_remix("https://douyin.com/video/xxx")

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
    
    print(f"改写后标题: {rewrite['rewritten']['title']}")
```
