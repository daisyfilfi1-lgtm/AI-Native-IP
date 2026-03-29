# 前后端数据结构对齐文档 - 方案A（简化版）

## 对齐状态：✅ 已完成

## 核心原则
- **标题 + 标签** 已足够
- 不做复杂情绪分析
- 不做八大元素映射
- 不做脚本模板映射

## API响应结构

```json
{
  "success": true,
  "error": "",
  "url": "https://www.douyin.com/video/xxxxx",
  "platform": "douyin",
  "video_id": "123456",
  "author": "作者名",
  
  "original_title": "90后宝妈靠副业月入过万...#宝妈副业",
  "title_clean": "90后宝妈靠副业月入过万...",
  "hook": "90后宝妈靠副业月入过万",
  "body": "分享3个真实方法",
  "tags": ["宝妈副业", "赚钱技巧"],
  
  "content_type": "money",
  
  "stats": {
    "play_count": 150000,
    "like_count": 8500,
    "share_count": 1200
  },
  
  "extract_method": "tikhub_douyin"
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| success | bool | 是否成功 |
| error | string | 错误信息 |
| url | string | 原始链接 |
| platform | string | 平台 (douyin/xiaohongshu) |
| video_id | string | 视频ID |
| author | string | 作者名 |
| original_title | string | 原始标题（含标签） |
| title_clean | string | 纯净标题（去掉#标签） |
| hook | string | 钩子（前半句/核心吸引点） |
| body | string | 正文（后半句/补充说明） |
| tags | string[] | 话题标签列表 |
| content_type | string | money/emotion/skill/life |
| stats | object | {play_count, like_count, share_count} |
| extract_method | string | 提取方式 |

## 标题拆分逻辑

```python
# 示例1: 有标点的标题
"32岁，我终于活成了别人羡慕的样子"
→ hook: "32岁"
→ body: "我终于活成了别人羡慕的样子"

# 示例2: 冒号分隔
"分享3个副业方法：宝妈也能月入过万"
→ hook: "分享3个副业方法"
→ body: "宝妈也能月入过万"

# 示例3: 短标题
"敬自已！与世界交手的第29年！"
→ hook: "敬自已！与世界交手的第29年！"
→ body: ""
```

## 实现文件

- **提取服务**: `backend/app/services/smart_content_extractor.py`
- **API路由**: `backend/app/routers/topic_recommendation_v4.py`
- **响应模型**: `ExtractedContentResponse`

## 数据流

```
抖音视频链接
    ↓
TIKHub API (fetch_one_video_by_share_url)
    ↓
_parse_response() 解析
    ↓
_clean_title() 清理标题
_split_title_structure() 拆分 hook/body
_detect_content_type() 检测类型
    ↓
ExtractedContent 数据类
    ↓
to_dict() API响应
```
