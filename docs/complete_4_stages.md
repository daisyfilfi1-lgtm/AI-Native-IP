# 完整4环节工作流

## 工作流概览

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  环节1      │  →  │  环节2      │  →  │  环节3      │  →  │  环节4      │
│  竞品发现   │     │  内容提取   │     │  标题改写   │     │  内容生成   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     输入                输入                输入                输入
   IP ID              视频URL            爆款标题+IP       改写标题+要点
     ↓                  ↓                  ↓                  ↓
     输出               输出               输出               输出
   视频列表          hook+body+tags     IP化改写标题      完整口播稿
```

## 各环节详解

### 环节1：竞品发现

**目的**：获取同类IP的近期爆款视频

**API**：`GET /strategy/v4/competitor-videos`

**核心功能**：
- 17个竞品账号同步
- 4维度排序（相关性/热度/竞争度/变现度）

---

### 环节2：内容提取

**目的**：从视频链接提取结构化标题

**API**：`POST /strategy/v4/extract-content`

**核心功能**：
- TIKHub API获取视频详情
- 标题拆分：hook（前半句）+ body（后半句）

---

### 环节3：标题改写

**目的**：爆款标题 + IP人设 → IP化改写标题

**API**：`POST /strategy/v3/title-rewrite`

**核心功能**：
- LLM语义级改写（理解爆款逻辑后重新创作）
- 保留数字/身份/对比等结构

---

### 环节4：内容生成 ✅

**目的**：改写标题 + IP素材 → 完整口播稿

**API**：`POST /strategy/v4/content-generate`

**核心设计**：**复用已打磨的"爆款原创"生成逻辑**

```python
# 直接调用 content_scenario.py 的 ScenarioThreeGenerator
from app.services.content_scenario import ScenarioThreeGenerator

generator = ScenarioThreeGenerator(ip_profile, style_profile)
result = await generator.generate(
    topic=title,      # 改写后的标题
    key_points=[hook, body],  # hook+body作为要点
    length="medium"
)
```

**为什么不重新写？**
- `content_scenario.py` 已经打磨了三大场景的生成逻辑
- `ScenarioThreeGenerator` 最灵活：支持自定义主题、有完整的一致性检查、人味度校验、多轮重写

**生成特点**：
- ✅ 不选四个固定脚本，根据内容和主题自生成
- ✅ 一致性检查：自动检测并修复风格偏差
- ✅ 人味度校验：避免AI腔，增加口语不完美感
- ✅ 多轮重写：校验不通过时自动重写

---

## 三个场景的生成统一

| 场景 | 前序环节 | 生成环节复用 |
|-----|---------|-------------|
| **推荐选题** | 数据源分析 → 选题推荐 | **ScenarioThreeGenerator** |
| **仿写爆款** | 爆款链接 → 结构提取 | **ScenarioThreeGenerator** |
| **爆款原创** | 自定义主题 | **ScenarioThreeGenerator**（原生） |

**统一优势**：
1. 生成质量一致
2. 维护成本低（只维护一套生成逻辑）
3. 已打磨的校验机制（一致性、人味度、多轮重写）

---

## 组合API

### 完整流程（环节2+3+4）
```
POST /strategy/v4/complete-pipeline?ip_id=xiaomin&url=https://...
```

输入视频链接，直接输出完整口播稿。

---

## 技术架构

### 数据流

```
CompetitorVideo (DB)
    ↓
SmartContentExtractor.extract() → ExtractedContent (hook/body/tags)
    ↓
TitleRewriteService.rewrite() → RewriteResult (IP化标题)
    ↓
ContentGenerationService.generate() 
    → 调用 ScenarioThreeGenerator.generate()
    → ContentResult (口播稿)
```

### 核心复用

```
content_scenario.py (已打磨)
├── ScenarioOneGenerator - 场景一：推荐选题
├── ScenarioTwoGenerator - 场景二：仿写爆款  
└── ScenarioThreeGenerator - 场景三：爆款原创 ★环节4复用

content_generation_service.py (环节4)
└── 直接调用 ScenarioThreeGenerator
```

---

## 实现文件

| 文件 | 说明 |
|-----|------|
| `app/services/competitor_sync_service.py` | 环节1：竞品同步 |
| `app/services/smart_content_extractor.py` | 环节2：内容提取 |
| `app/services/title_rewrite_service.py` | 环节3：LLM语义改写 |
| `app/services/content_scenario.py` | **已打磨的三大场景生成逻辑** |
| `app/services/content_generation_service.py` | 环节4（复用上述逻辑） |
| `app/routers/topic_recommendation_v4.py` | 所有API路由 |

---

## 完整示例

```bash
# 一键完整流程
curl -X POST "http://localhost:8000/strategy/v4/complete-pipeline?ip_id=xiaomin&url=https://douyin.com/video/xxx"

# 返回：
{
  "success": true,
  "stage": "complete",
  "pipeline": {
    "stage2_extraction": {
      "title": "90后宝妈靠副业月入过万...",
      "hook": "90后宝妈靠副业月入过万",
      "body": "分享3个真实方法"
    },
    "stage3_rewrite": {
      "rewritten": {
        "title": "UI设计师靠AI接私单月入3万...",
        "hook": "UI设计师靠AI接私单月入3万",
        "body": "分享我的3个获客渠道"
      },
      "analysis": "原标题抓住宝妈赚钱希望，用身份+收入+干货结构"
    },
    "stage4_generation": {
      "content": "（完整口播稿，经过一致性校验和人味度优化）",
      "score": 0.85,
      "word_count": 320
    }
  }
}
```

---

## 注意事项

1. **环节4不复用ScenarioTwoGenerator**：ScenarioTwo依赖竞品原文做结构分析，而环节4的输入只有标题
2. **环节4复用ScenarioThreeGenerator**：更灵活，只需要主题和要点
3. **统一生成逻辑**：三个场景的生成环节都用同一套打磨好的逻辑
