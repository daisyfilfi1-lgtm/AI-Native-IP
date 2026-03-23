"""
本地测试服务器 - 用于快速调试 CORS 和上传问题

使用方法：
    cd backend
    python test_server.py

然后浏览器访问 http://localhost:8000/docs 测试 API
"""
import os
import sys

# 设置本地环境变量
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/ip_factory"
os.environ["CORS_ALLOW_ALL"] = "true"  # 本地测试允许所有来源
os.environ["STORAGE_LOCAL_DISABLED"] = "false"
os.environ["STORAGE_LOCAL_PATH"] = "./uploads"

# 确保上传目录存在
os.makedirs("./uploads", exist_ok=True)

from app.main import app
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("本地测试服务器启动")
    print("=" * 60)
    print("API 文档: http://localhost:8000/docs")
    print("健康检查: http://localhost:8000/health")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
