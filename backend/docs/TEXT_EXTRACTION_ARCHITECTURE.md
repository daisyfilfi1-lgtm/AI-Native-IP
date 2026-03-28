# 文本提取服务架构文档

## 概述

新版文本提取服务采用**多策略融合**架构，支持多种短视频平台的链接解析和文本提取。

## 架构图

```
用户输入链接
    ↓
┌─────────────────────────────────────────┐
│  link_resolver.resolve_any_url()         │
│  • 短链解析 (抖音/小红书/快手/B站)        │
│  • 视频ID提取                           │
│  • 平台识别                             │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  text_extractor.extract_text()           │
│  智能选择提取策略：                      │
│                                          │
│  1. TikHub API (优先)                   │
│     • 抖音 Web 单条接口                  │
│     • Hybrid 通用接口                    │
│                                          │
│  2. Web 爬取 (备选)                     │
│     • 抖音移动端页面                     │
│     • 小红书 SSR 数据                    │
│     • 快手页面                           │
│     • B站页面                            │
│                                          │
│  3. yt-dlp (兜底)                       │
│     • 多平台元数据提取                   │
└─────────────────────────────────────────┘
    ↓
返回 ExtractResult {text, method, metadata}
```

## 核心组件

### 1. link_resolver.py - 链接解析器

**功能：**
- 多平台短链解析（抖音 v.douyin.com、小红书 xhslink.com、快手、B站）
- 视频ID提取
- 链接有效性检查

**支持的平台：**
| 平台 | 短链域名 | 长链格式 |
|-----|---------|---------|
| 抖音 | v.douyin.com | /video/{id} |
| 小红书 | xhslink.com | /explore/{id} |
| 快手 | v.kuaishou.com | /short-video/{id} |
| B站 | b23.tv | /video/{BVid} |

### 2. text_extractor.py - 统一提取服务

**功能：**
- 整合多种提取策略
- 自动选择最优方案
- 统一的错误处理和元数据返回

**提取策略优先级：**
1. **TikHub API** - 官方数据，最准确
2. **Web 爬取** - 不依赖第三方 API
3. **yt-dlp** - 通用解决方案

### 3. competitor_text_extraction.py - 兼容层

**功能：**
- 提供向后兼容的接口
- 主入口：`extract_competitor_text_with_fallback()`

## 使用方式

### 基础使用

```python
from app.services.text_extractor import extract_text

result = await extract_text("https://v.douyin.com/xxxxx")

if result.success:
    print(f"提取成功: {result.text[:100]}")
    print(f"使用方法: {result.method}")
    print(f"平台: {result.metadata.get('platform')}")
else:
    print(f"提取失败: {result.error}")
```

### 指定优先策略

```python
# 优先使用 Web 爬取
result = await extract_text(url, prefer_method="web_scrape")
```

### 带诊断信息

```python
from app.services.competitor_text_extraction import extract_competitor_text_with_fallback

result = await extract_competitor_text_with_fallback(url)

if result["success"]:
    text = result["text"]
    method = result["method"]
    metadata = result["metadata"]
else:
    error = result["error"]
```

## 错误处理

### 常见错误及解决方案

| 错误类型 | 错误信息 | 解决方案 |
|---------|---------|---------|
| API 未配置 | TIKHUB_API_KEY 未配置 | 设置环境变量或联系管理员 |
| API 权限不足 | 403 Forbidden | 检查 TikHub 后台权限配置 |
| 视频不存在 | 404 Not Found | 检查链接是否有效 |
| 请求频繁 | 429 Rate Limit | 稍后重试 |
| Web 爬取失败 | 反爬限制 | 尝试其他链接或手动输入 |

### 手动输入后备

当自动提取失败时，前端提供手动输入模式：

1. 用户点击"手动粘贴文案"
2. 粘贴视频标题和文案
3. 系统绕过链接提取，直接使用用户提供的内容

## 配置

### 环境变量

```bash
# TikHub API
TIKHUB_API_KEY=your_api_key

# yt-dlp（可选）
REMIX_YTDLP_FALLBACK=1
```

### 安装依赖

```bash
# yt-dlp（可选，用于增强提取能力）
pip install yt-dlp
```

## 性能优化

### 1. 超时设置
- 链接解析：15秒
- TikHub API：60秒
- Web 爬取：15秒
- yt-dlp：45秒

### 2. 重试机制
- 短链解析失败时，尝试不同 UA
- Web 爬取尝试多个端点

### 3. 内容缓存
- 提取结果可缓存，避免重复请求

## 扩展指南

### 添加新平台支持

1. 在 `link_resolver.py` 添加平台识别模式
2. 在 `text_extractor.py` 添加 Web 爬取逻辑

示例：

```python
# link_resolver.py
PLATFORM_PATTERNS = {
    "new_platform": [r"new\.com", r"share\.new\.com"],
}

# text_extractor.py
async def _extract_new_platform_web(url: str) -> str:
    # 实现爬取逻辑
    pass
```

### 添加新的提取策略

1. 实现提取函数，返回 `ExtractResult`
2. 在 `extract_text()` 中添加策略

## 监控与日志

### 关键日志

```python
logger.info(f"开始提取文本: {url}")
logger.info(f"链接解析完成: platform={platform}")
logger.info(f"提取成功: method={method}, length={len(text)}")
logger.warning(f"提取失败: {error}")
```

### 指标收集

- 提取成功率
- 各策略使用比例
- 平均提取时间
- 平台分布

## 安全考虑

1. **URL 过滤**：只处理 http/https 链接
2. **内容长度限制**：最大 12000 字符
3. **超时控制**：防止长时间阻塞
4. **错误信息脱敏**：不暴露敏感配置信息
