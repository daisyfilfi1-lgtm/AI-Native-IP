# 内容语义标签 · 参考术语表（非强制）

不同 IP 的定位、受众与内容策略不同，**下表仅供产品与运营对齐口径时参考**，不是全站唯一标准。

**技术架构要求**：实际自动打标以各 IP 在 **`tag_config.tag_categories`** 中配置的术语表为准（可增删改字段与候选值）；未单独配置时，后端会使用本文档中的四维与候选值作为**默认引导**（仍建议尽快按 IP 落库配置）。

---

## 四维语义（字段 key 建议）

| 维度 | 建议字段 key (`type`) | 说明 |
|------|------------------------|------|
| 主题域 | `theme_domain` | 内容所属主题大类 |
| 情绪锚点 | `emotion_anchor` | 面向用户的主要情绪牵引 |
| 叙事结构 | `narrative_structure` | 内容组织方式 |
| 人设模式 | `persona_mode` | 表达者角色/口吻 |

---

## 参考候选值（可按 IP 裁剪）

### 1. 主题域 `theme_domain`

- 方法论与认知  
- 情感共情与价值观  
- 技术或产品展示  
- 团队实力  
- 美好生活展示  
- 个人经历和故事  
- 热点话题观点  
- 第三方对话  
- 其他  

### 2. 情绪锚点 `emotion_anchor`

- 愤怒  
- 焦虑  
- 希望  
- 共鸣  
- 猎奇  
- 认知深度  
- 娱乐  
- 其他  

### 3. 叙事结构 `narrative_structure`

- 痛点开场  
- 故事反转  
- 干货清单  
- 对比论证  
- 反常识  
- 其他  

### 4. 人设模式 `persona_mode`

- 闺蜜吐槽  
- 专家科普  
- 经历分享  
- 旁观者观察  
- 自定义  

---

## 写入 Memory 配置的示例（`POST /api/v1/config/memory`）

将 `tag_categories` 配好后，录入流水线会**严格只从候选值里**选标（见 `docs/AI_CONFIG.md`）。

```json
{
  "tag_config": {
    "config_id": "cfg_tag_demo",
    "ip_id": "your_ip_id",
    "updated_by": "ops",
    "tag_categories": [
      {
        "name": "主题域",
        "level": 1,
        "type": "theme_domain",
        "values": [
          { "value": "方法论与认知", "label": "方法论与认知", "color": "#6366f1", "enabled": true },
          { "value": "情感共情与价值观", "label": "情感共情与价值观", "color": "#8b5cf6", "enabled": true },
          { "value": "技术或产品展示", "label": "技术或产品展示", "color": "#0ea5e9", "enabled": true },
          { "value": "团队实力", "label": "团队实力", "color": "#14b8a6", "enabled": true },
          { "value": "美好生活展示", "label": "美好生活展示", "color": "#22c55e", "enabled": true },
          { "value": "个人经历和故事", "label": "个人经历和故事", "color": "#eab308", "enabled": true },
          { "value": "热点话题观点", "label": "热点话题观点", "color": "#f97316", "enabled": true },
          { "value": "第三方对话", "label": "第三方对话", "color": "#ec4899", "enabled": true },
          { "value": "其他", "label": "其他", "color": "#94a3b8", "enabled": true }
        ]
      },
      {
        "name": "情绪锚点",
        "level": 1,
        "type": "emotion_anchor",
        "values": [
          { "value": "愤怒", "label": "愤怒", "color": "#ef4444", "enabled": true },
          { "value": "焦虑", "label": "焦虑", "color": "#f59e0b", "enabled": true },
          { "value": "希望", "label": "希望", "color": "#22c55e", "enabled": true },
          { "value": "共鸣", "label": "共鸣", "color": "#3b82f6", "enabled": true },
          { "value": "猎奇", "label": "猎奇", "color": "#a855f7", "enabled": true },
          { "value": "认知深度", "label": "认知深度", "color": "#0d9488", "enabled": true },
          { "value": "娱乐", "label": "娱乐", "color": "#ec4899", "enabled": true },
          { "value": "其他", "label": "其他", "color": "#94a3b8", "enabled": true }
        ]
      },
      {
        "name": "叙事结构",
        "level": 1,
        "type": "narrative_structure",
        "values": [
          { "value": "痛点开场", "label": "痛点开场", "color": "#64748b", "enabled": true },
          { "value": "故事反转", "label": "故事反转", "color": "#6366f1", "enabled": true },
          { "value": "干货清单", "label": "干货清单", "color": "#0ea5e9", "enabled": true },
          { "value": "对比论证", "label": "对比论证", "color": "#14b8a6", "enabled": true },
          { "value": "反常识", "label": "反常识", "color": "#f97316", "enabled": true },
          { "value": "其他", "label": "其他", "color": "#94a3b8", "enabled": true }
        ]
      },
      {
        "name": "人设模式",
        "level": 1,
        "type": "persona_mode",
        "values": [
          { "value": "闺蜜吐槽", "label": "闺蜜吐槽", "color": "#ec4899", "enabled": true },
          { "value": "专家科普", "label": "专家科普", "color": "#3b82f6", "enabled": true },
          { "value": "经历分享", "label": "经历分享", "color": "#22c55e", "enabled": true },
          { "value": "旁观者观察", "label": "旁观者观察", "color": "#8b5cf6", "enabled": true },
          { "value": "自定义", "label": "自定义", "color": "#94a3b8", "enabled": true }
        ]
      }
    ]
  }
}
```

---

## 与自动打标的关系

| 场景 | 行为 |
|------|------|
| IP 已配置 `tag_categories` | 仅使用配置中的字段与 `values[].value`，**强约束**，保证业务口径一致 |
| IP 未配置 | 使用本文档四维与候选值作为 **默认参考**（后端 prompt + 取值校验），便于冷启动 |

详细环境变量与接口说明见 **`docs/AI_CONFIG.md`**。
