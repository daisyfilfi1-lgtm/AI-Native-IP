# 环节4：改写标题 + IP素材 → 内容生成

## 核心设计

**复用已打磨的"爆款原创"生成逻辑**

三个场景（推荐选题、仿写爆款、爆款原创）的生成环节，统一调用 `content_scenario.py` 中已打磨好的 `ScenarioThreeGenerator`。

## 为什么不重新写生成逻辑？

现有的 `content_scenario.py` 已经打磨了三大场景的生成逻辑：

| 场景 | 生成器 | 特点 |
|-----|-------|------|
| 场景一：推荐选题 | ScenarioOneGenerator | 热点+IP匹配，自动生成 |
| 场景二：仿写爆款 | ScenarioTwoGenerator | 竞品分析+IP改写，对抗校验 |
| 场景三：爆款原创 | ScenarioThreeGenerator | 自定义主题+IP风格，一致性检查 |

**环节4直接复用 ScenarioThreeGenerator**，因为它最灵活：
- 支持自定义主题（传入改写后的标题）
- 支持关键要点（传入hook+body）
- 有完整的一致性检查和自动重写机制
- 有风格对齐和人味度校验

## 代码复用

```python
# 环节4的服务
class ContentGenerationService:
    async def generate(self, ip_id, title, hook, body, content_type):
        # 直接调用已打磨的ScenarioThreeGenerator
        from app.services.content_scenario import ScenarioThreeGenerator
        
        generator = ScenarioThreeGenerator(
            ip_profile=ip_profile,
            style_profile=style_profile
        )
        
        result = await generator.generate(
            topic=title,           # 改写后的标题作为主题
            key_points=[hook, body], # hook+body作为要点
            length=length_map[content_type]
        )
        
        return result
```

## 生成流程（复用ScenarioThreeGenerator）

```
输入：改写后的标题 + hook + body
    ↓
构建IP画像 + 风格画像
    ↓
调用 ScenarioThreeGenerator.generate()
    ├── Step 1: 构建Prompt（主题+要点+风格约束）
    ├── Step 2: LLM生成（含一致性失败自动重试）
    ├── Step 3: 风格人味度校验（失败则重写）
    └── Step 4: 质量评分
    ↓
输出：完整口播稿
```

## 生成的特点

1. **不选四个固定脚本**：根据内容和主题自生成
2. **一致性检查**：自动检测并修复风格偏差
3. **人味度校验**：避免AI腔，增加口语不完美感
4. **多轮重写**：校验不通过时自动重写（最多2-3轮）

## API端点

```
POST /strategy/v4/content-generate
```

**请求体：**
```json
{
  "ip_id": "xiaomin",
  "title": "90后UI设计师靠AI接私单月入3万，分享我的3个获客渠道",
  "hook": "90后UI设计师靠AI接私单月入3万",
  "body": "分享我的3个获客渠道",
  "content_type": "money",
  "target_duration": 60
}
```

**返回：**
```json
{
  "success": true,
  "ip_id": "xiaomin",
  "ip_name": "小敏",
  "title": "90后UI设计师靠AI接私单月入3万，分享我的3个获客渠道",
  "content": "（完整口播稿，经过一致性校验和人味度优化）",
  "score": 0.85,
  "word_count": 320,
  "estimated_duration": 80
}
```

## 完整4环节工作流

```
环节1: 竞品发现
    ↓ 获取竞品视频列表
环节2: 内容提取  
    ↓ 标题 → hook + body
环节3: 标题改写（LLM语义级）
    ↓ 爆款结构 + IP视角
环节4: 内容生成（复用ScenarioThreeGenerator）
    ↓ 标题 + hook/body → 口播稿
完整视频脚本
```

## 实现文件

- `app/services/content_scenario.py` - **已打磨的三大场景生成逻辑**
- `app/services/content_generation_service.py` - 环节4（复用上述逻辑）
- `app/routers/topic_recommendation_v4.py` - API路由

## 注意事项

1. **不复用ScenarioTwoGenerator**：虽然也是爆款改写，但它依赖竞品原文做结构分析
2. **复用ScenarioThreeGenerator**：更灵活，只需要主题和要点，适合环节4的输入格式
3. **保持生成逻辑统一**：三个场景都用同一套生成逻辑，确保质量一致
