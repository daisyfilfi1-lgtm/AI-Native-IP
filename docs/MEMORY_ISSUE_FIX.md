# 文件上传内存问题修复指南

## 问题描述

在 Netlify + Railway 架构下，上传一个 11KB 的文件时，内存突然飙升至 4GB。

## 根本原因分析

### 1. 前端 API 路由配置混乱（主要原因）

**问题**：
- 前端配置中存在双重路由可能：Netlify 边缘代理和浏览器直连
- 如果环境变量没有正确传递，上传请求可能经过 Next.js Serverless 函数
- Serverless 函数处理 multipart/form-data 时可能导致内存暴增

**解决方案**：
- 在 `netlify.toml` 中明确设置 `NEXT_PUBLIC_API_DIRECT_ORIGIN`
- 在 `apiBaseUrl.ts` 中优先使用直连方式
- 添加上传文件大小限制（10MB）

### 2. FastAPI 文件上传未优化

**问题**：
- 使用 `await file.read()` 一次性读取整个文件
- 没有流式处理大文件
- 缺少内存监控和日志

**解决方案**：
- 实现分块读取（64KB chunks）
- 添加内存监控中间件
- 添加详细的调试日志
- 限制文件大小为 10MB

### 3. 潜在的本地 Embedding 模型加载

**问题**：
- 如果 API 调用失败且环境变量被误设，可能意外加载 PyTorch 模型（数 GB）

**解决方案**：
- 确保 `LOCAL_EMBEDDING_ENABLED` 未设置或为 `false`
- 使用云端 Embedding API（OpenAI/Cohere/腾讯云）

---

## 修复内容

### 1. 前端修复 (`frontend/lib/api.ts`)

```typescript
// 添加上传文件大小限制
const MAX_FILE_SIZE = 10 * 1024 * 1024;
if (file.size > MAX_FILE_SIZE) {
  throw new Error(`文件过大，最大支持 ${MAX_FILE_SIZE / 1024 / 1024}MB`);
}

// 配置流式上传和内存限制
const response = await this.client.post<MemoryUploadResponse>('/memory/upload', formData, {
  timeout: 60000,
  maxContentLength: 10 * 1024 * 1024,  // 明确限制 10MB
  maxBodyLength: 10 * 1024 * 1024,
  // ...
});
```

### 2. 后端修复 (`backend/app/routers/memory.py`)

```python
# 流式读取文件内容，避免一次性加载大文件
chunks = []
total_size = 0
chunk_size = 64 * 1024  # 64KB chunks

while True:
    chunk = await file.read(chunk_size)
    if not chunk:
        break
    total_size += len(chunk)
    if total_size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="文件过大")
    chunks.append(chunk)
```

### 3. 内存监控 (`backend/app/main.py`)

```python
class MemoryMonitorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 监控请求前后的内存变化
        mem_before = process.memory_info().rss / 1024 / 1024
        response = await call_next(request)
        mem_after = process.memory_info().rss / 1024 / 1024
        
        if mem_after - mem_before > 100:  # 超过 100MB
            logger.warning(f"内存增长异常: {mem_after - mem_before:.1f}MB")
```

---

## 部署步骤

### 1. 更新 Railway 环境变量

在 Railway Dashboard → Variables 中添加/更新：

```
# 必须设置
MAX_UPLOAD_SIZE = 10485760  # 10MB in bytes

# 禁用本地 Embedding，避免意外加载大模型
LOCAL_EMBEDDING_ENABLED = false

# 可选：启用内存日志
PYTHONUNBUFFERED = 1
```

### 2. 更新 Netlify 环境变量

在 Netlify Dashboard → Site settings → Environment variables：

```
# 确保设置（不要删除）
NEXT_PUBLIC_API_DIRECT_ORIGIN = https://ai-native-ip-production.up.railway.app

# 删除以下变量（如果存在）
# NEXT_PUBLIC_API_URL  ← 删除这个，它会干扰直连配置
```

### 3. 重新部署

1. 提交代码更改到 Git
2. 推送到 main 分支
3. 等待 Railway 自动部署
4. 等待 Netlify 自动部署

---

## 验证修复

### 方法 1：查看日志

在 Railway 日志中查看：

```
[upload_memory_file] 开始上传: ip_id=xxx, filename=test.txt, memory_before=45.2MB
[upload_memory_file] 文件读取完成: size=11264 bytes, chunks=1
[upload_memory_file] 上传完成: file_id=xxx, memory_after=46.1MB, delta=+0.9MB
```

如果看到 `delta` 超过 100MB，说明仍有问题。

### 方法 2：浏览器开发者工具

1. 打开浏览器开发者工具 → Network
2. 上传一个文件
3. 检查请求 URL：
   - ✅ 正确：`https://ai-native-ip-production.up.railway.app/api/v1/memory/upload`
   - ❌ 错误：`https://your-site.netlify.app/api/v1/memory/upload`

### 方法 3：内存监控端点

```bash
# 检查应用健康状态
curl https://ai-native-ip-production.up.railway.app/health

# 查看内存使用（需要在代码中添加端点）
```

---

## 如果问题仍然存在

### 检查清单

1. **环境变量是否正确设置？**
   ```bash
   # 在 Railway 容器内检查
   echo $NEXT_PUBLIC_API_DIRECT_ORIGIN
   echo $LOCAL_EMBEDDING_ENABLED
   ```

2. **前端是否真的直连？**
   - 浏览器 DevTools → Network → 检查请求 URL

3. **Railway 容器内存限制？**
   - Railway 免费版内存有限，检查是否需要升级

4. **是否有其他中间件干扰？**
   - 检查是否有 Cloudflare 等其他代理

### 临时解决方案

如果问题仍然存在，可以：

1. **禁用文件上传功能**（临时）
2. **直接使用 Railway 域名上传**（绕过 Netlify）
3. **使用预签名 URL 直传云存储**（推荐长期方案）

---

## 长期建议

1. **使用预签名 URL 直传 S3/OSS**
   - 浏览器直接上传文件到对象存储
   - 后端只处理文件元数据
   - 完全避免内存问题

2. **添加文件大小限制**
   - 前端：10MB
   - 后端：10MB
   - Nginx/代理层：10MB

3. **使用分片上传**
   - 大文件分片上传
   - 支持断点续传
   - 减少单次请求内存占用
