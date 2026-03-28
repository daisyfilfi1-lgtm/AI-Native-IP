# 本地测试指南

在推送到 Railway 之前，先在本地完成所有调试，提高效率。

## 🚀 快速开始

### 1. 启动本地后端

```bash
cd backend

# 方法1：使用测试脚本（推荐）
python test_server.py

# 方法2：直接启动（如果有 PostgreSQL）
# 确保 DATABASE_URL 指向本地数据库
uvicorn app.main:app --reload --port 8000
```

后端启动后会显示：
```
API 文档: http://localhost:8000/docs
健康检查: http://localhost:8000/health
```

### 2. 配置前端连接本地后端

```bash
cd frontend

# 已经创建了 .env.local 文件
# 内容：NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1

npm run dev
```

前端启动后访问 http://localhost:3000

### 3. 测试文件上传

#### 方法 A：使用浏览器（最直观）

1. 打开 http://localhost:3000
2. 选择一个 IP
3. 上传文件
4. 打开浏览器 DevTools → Network 查看请求详情

#### 方法 B：使用命令行（最快）

Windows:
```bash
cd backend
test_upload.bat test.txt ip_test_001
```

Mac/Linux:
```bash
cd backend
chmod +x test_upload.sh
./test_upload.sh test.txt ip_test_001
```

#### 方法 C：使用 curl

```bash
# 创建测试文件
echo "Hello World" > test.txt

# 上传测试
curl -X POST http://localhost:8000/api/v1/memory/upload \
  -F "ip_id=ip_test_001" \
  -F "file=@test.txt"
```

## 🔍 调试技巧

### 查看后端日志

启动后端后，所有请求都会打印日志：
```
INFO:[Request] POST /api/v1/memory/upload from http://localhost:3000
INFO:[Response] POST /api/v1/memory/upload - 200
```

### 测试 CORS

```bash
# 测试跨域请求
curl -X OPTIONS http://localhost:8000/api/v1/memory/upload \
  -H "Origin: https://ai-native-ip.netlify.app" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

如果看到 `Access-Control-Allow-Origin: *`，说明 CORS 配置正确。

### 测试内存使用

上传大文件时观察内存：
```bash
# 创建 5MB 测试文件
dd if=/dev/zero of=large_test.bin bs=1M count=5

# 上传并观察日志
./test_upload.sh large_test.bin
```

## ✅ 验证清单

在本地验证以下功能正常后再推送到 Railway：

- [ ] 健康检查: http://localhost:8000/health
- [ ] API 文档: http://localhost:8000/docs
- [ ] 文件上传（小文件 < 1MB）
- [ ] 文件上传（大文件 > 5MB）
- [ ] CORS 跨域请求正常
- [ ] 数据库写入正常
- [ ] 前端页面加载正常
- [ ] 前端能成功上传文件

## 🚀 推送到 Railway

本地测试全部通过后：

```bash
# 提交代码
git add .
git commit -m "fix: 修复文件上传问题"
git push origin master

# 推送到 Railway 后，记得删除 CORS_ALLOW_ALL=true
# 改为具体的域名：CORS_ORIGINS=https://your-site.netlify.app
```

## 🐛 常见问题

### 问题 1: 后端启动失败 "DATABASE_URL not set"

解决：
```bash
# Windows
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ip_factory

# Mac/Linux
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ip_factory
```

### 问题 2: 前端连接不上后端

检查：
1. 后端是否真的启动了（看端口 8000）
2. `.env.local` 文件内容是否正确
3. 浏览器 Network 面板看请求 URL

### 问题 3: CORS 错误

解决：
- 本地测试时设置了 `CORS_ALLOW_ALL=true`
- 或者确保 `.env.local` 中的 API_URL 是 `http://127.0.0.1:8000`

## 📞 需要帮助？

如果在本地测试遇到问题：

1. 复制完整的错误信息
2. 查看后端控制台输出
3. 查看浏览器 DevTools Console
4. 然后反馈给我
