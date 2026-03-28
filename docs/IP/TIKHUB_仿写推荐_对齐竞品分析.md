# TikHub 仿写推荐：与《竞品分析》对齐

来源文档：`docs/IP知识库/竞品分析.docx`（20 个抖音对标账号）。

## 重要说明

- 《竞品分析》里的链接均为 **抖音主页**，**不是**小红书话题 `page_id`。
- `TIKHUB_XHS_TOPIC_PAGE_IDS` 需要的是 **小红书话题标签 ID**（与抖音对标是两条线：抖音靠低粉榜 + 关键词匹配；小红书靠话题笔记流）。

## 已在仓库配置的变量（见 `backend/.env.example`）

| 变量 | 作用 |
|------|------|
| `TIKHUB_REMIX_EXTRA_KEYWORDS` | 与文档赛道一致的关键词，参与 **抖音低粉爆款榜** 标题匹配（推荐必配）。 |
| `TIKHUB_XHS_TOPIC_PAGE_IDS` | 小红书话题 `page_id`，逗号分隔；用于拉取话题下笔记链接做仿写推荐。 |

## 如何填写 `TIKHUB_XHS_TOPIC_PAGE_IDS`

1. 在小红书 App 搜索与 IP 赛道接近的话题，例如：**女性创业**、**宝妈副业**、**副业**、**搞钱**、**私域**、**知识付费**、**独立女性**。
2. 进入话题页 → 分享 → 复制链接；或在 TikHub 控制台调用 `GET /api/v1/xiaohongshu/app_v2/get_topic_info`，对候选 `page_id` 试跑直到返回正常话题名。
3. `page_id` 一般为 **24 位十六进制字符串**（示例见 TikHub OpenAPI：`5c014b045b29cb0001ead530`）。
4. 将 3～8 个验证通过的 ID 写入 Railway：`TIKHUB_XHS_TOPIC_PAGE_IDS=id1,id2,id3`

## 校验脚本（需已配置 `TIKHUB_API_KEY`）

```bash
cd backend
set TIKHUB_API_KEY=你的密钥
py -3 scripts/tikhub_try_topic_info.py 5c014b045b29cb0001ead530
```

脚本会打印 `get_topic_info` 返回的话题名称，确认无误后再写入环境变量。
