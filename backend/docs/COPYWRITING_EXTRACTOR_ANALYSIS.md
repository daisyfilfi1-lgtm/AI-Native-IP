# 文案提取工具技术分析与集成方案

## 主流文案提取工具技术栈分析

### 1. anytocopy.com / 马力文案提取器 技术推测

#### 方案A：yt-dlp 基础架构（最可能）
```
技术栈：
- 后端：Python + yt-dlp
- 前端：Next.js/React
- 部署：Vercel/Cloudflare Workers

特点：
✓ 支持 1000+ 站点
✓ 提取标题、描述、评论
✗ 需要服务器资源（yt-dlp较重）
```

#### 方案B：多API聚合服务
```
技术栈：
- 抖音：TikHub / 自建解析
- 小红书：自建爬虫
- B站：官方API
- 快手：自建爬虫

特点：
✓ 准确率高
✗ 维护成本高
✗ 需要处理反爬
```

#### 方案C：浏览器插件+云端
```
技术栈：
- 浏览器扩展提取页面数据
- 云端存储和分享

特点：
✓ 绕过反爬限制
✗ 需要用户安装插件
```

---

## 我们可以借鉴的技术

### 方案1：增强 yt-dlp 集成（推荐）

yt-dlp 是目前最成熟的开源方案，支持提取：
- 视频标题、描述
- 评论（部分平台）
- 字幕/弹幕

**集成代码：**
```python
import yt_dlp

ydl_opts = {
    'skip_download': True,
    'writesubtitles': True,
    'writeautomaticsub': True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    text = f"{info.get('title', '')}\n\n{info.get('description', '')}"
```

**我们已经在做了** - 见 `text_extractor.py` 中的 `extract_with_ytdlp()`

---

### 方案2：集成第三方文案提取API

#### 选项A：RapidAPI - Social Media Scraper
```
URL: https://rapidapi.com/category/Social%20Media
价格：$0-50/月
支持：抖音、TikTok、Instagram 等

优点：
- 稳定，不需要自己维护
- 即开即用

缺点：
- 收费
- 有调用限制
```

#### 选项B：SerpAPI + 站点特定搜索
```python
# 通过 Google 搜索获取视频标题和描述
from serpapi import GoogleSearch

params = {
    "q": f"site:douyin.com {video_id}",
    "api_key": "your_key"
}
search = GoogleSearch(params)
results = search.get_dict()
```

---

### 方案3：内嵌 anytocopy.com（快速方案）

如果自研成本太高，可以直接集成第三方工具：

#### 实现方式A：iframe 嵌入
```tsx
// 前端页面嵌入
<div className="w-full h-[600px]">
  <iframe 
    src={`https://www.anytocopy.com/extract?url=${encodeURIComponent(videoUrl)}`}
    className="w-full h-full border rounded-lg"
  />
</div>
```

#### 实现方式B：链接跳转 + 结果回调
```tsx
// 在新标签页打开，用户复制后粘贴回来
<a 
  href={`https://www.anytocopy.com/extract?url=${videoUrl}`}
  target="_blank"
  rel="noopener noreferrer"
>
  🔗 去 anytocopy 提取文案
</a>

// 回到我们的页面手动粘贴
<textarea 
  placeholder="粘贴提取的文案..."
  onChange={handleManualInput}
/>
```

---

### 方案4：自建浏览器扩展（中长期）

**架构：**
```
用户安装浏览器插件
       ↓
在抖音/小红书页面注入脚本
       ↓
提取页面中的文案数据
       ↓
一键发送到 IP工厂
```

**优点：**
- 绕过所有反爬限制
- 提取准确率高（直接读取页面数据）
- 用户体验好

**缺点：**
- 开发成本高
- 需要用户安装
- 各平台维护

---

## 推荐实施方案

### 阶段1：快速增强（本周）

1. **完善 yt-dlp 支持**
   - 确保 Docker 镜像包含 yt-dlp
   - 添加环境变量控制启用

2. **添加 anytocopy 备用链接**
   - 当提取失败时显示
   - 用户跳转提取后手动粘贴

3. **优化手动输入体验**
   - 已经实现

### 阶段2：服务集成（2周内）

1. **调研 RapidAPI 方案**
   - 测试准确率
   - 评估成本

2. **增强 Web 爬取**
   - 针对抖音/小红书优化
   - 添加更多 User-Agent 轮换

### 阶段3：深度集成（1个月）

1. **浏览器扩展开发**
   - Chrome/Edge 插件
   - 与主站打通

---

## 具体代码实现：添加 anytocopy 备用

### 前端修改

```tsx
// 当提取失败时显示备用选项
{extractionFailed && (
  <div className="mt-4 p-4 bg-background-tertiary rounded-lg">
    <p className="text-sm text-foreground-secondary mb-3">
      自动提取失败，你可以：
    </p>
    
    {/* 选项1：使用第三方工具 */}
    <a 
      href={`https://www.anytocopy.com/extract?url=${encodeURIComponent(url)}`}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-2 p-3 bg-primary-500/10 rounded-lg hover:bg-primary-500/20 transition-colors mb-3"
    >
      <ExternalLink className="w-4 h-4 text-primary-400" />
      <span className="text-sm text-primary-400">
        去 anytocopy.com 提取文案
      </span>
    </a>
    
    {/* 选项2：手动输入 */}
    <button
      onClick={() => setManualMode(true)}
      className="flex items-center gap-2 p-3 border border-border rounded-lg hover:bg-background-elevated transition-colors w-full"
    >
      <Pencil className="w-4 h-4 text-foreground-secondary" />
      <span className="text-sm text-foreground-secondary">
        手动粘贴文案
      </span>
    </button>
  </div>
)}
```

### 备选：聚合多个第三方工具

```tsx
const THIRD_PARTY_EXTRACTORS = [
  {
    name: 'anytocopy',
    url: (videoUrl: string) => `https://www.anytocopy.com/extract?url=${encodeURIComponent(videoUrl)}`,
    icon: '🔗',
    description: '支持抖音、小红书、B站',
  },
  {
    name: '马力文案',
    url: (videoUrl: string) => `https://www.extraction.tool/?url=${encodeURIComponent(videoUrl)}`,
    icon: '⚡',
    description: '提取速度快',
  },
  {
    name: '文案提取神器',
    url: (videoUrl: string) => `https://copywriter.tools/extract?url=${encodeURIComponent(videoUrl)}`,
    icon: '📝',
    description: '支持批量提取',
  },
];

// 显示多个选项
<div className="grid grid-cols-1 gap-2">
  {THIRD_PARTY_EXTRACTORS.map(tool => (
    <a
      key={tool.name}
      href={tool.url(videoUrl)}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-3 p-3 border border-border rounded-lg hover:bg-background-elevated transition-colors"
    >
      <span className="text-lg">{tool.icon}</span>
      <div className="flex-1">
        <p className="text-sm font-medium text-foreground">{tool.name}</p>
        <p className="text-xs text-foreground-secondary">{tool.description}</p>
      </div>
      <ExternalLink className="w-4 h-4 text-foreground-tertiary" />
    </a>
  ))}
</div>
```

---

## 自研 vs 集成的决策

| 维度 | 自研 | 集成第三方 | 混合方案 |
|-----|------|-----------|---------|
| **开发成本** | 高 | 低 | 中 |
| **准确率** | 中-高 | 高 | 高 |
| **稳定性** | 需维护 | 依赖第三方 | 中等 |
| **成本** | 服务器费用 | API费用 | 混合 |
| **用户体验** | 一致 | 跳转割裂 | 较好 |
| **数据安全** | 高 | 需传输给第三方 | 中等 |

**推荐：混合方案**
- 优先自研（成本低，可控）
- 第三方作为后备（确保可用性）
- 手动输入兜底（100%可用）

---

## 下一步行动

1. **立即实施**：
   - [ ] 在提取失败页面添加 anytocopy 链接
   - [ ] 部署 yt-dlp 增强版

2. **本周完成**：
   - [ ] 测试 yt-dlp 各平台提取效果
   - [ ] 评估 RapidAPI 成本

3. **本月规划**：
   - [ ] 决定是否开发浏览器扩展
   - [ ] 评估是否需要购买第三方 API 服务
