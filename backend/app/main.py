import os
import logging

from app.env_loader import load_backend_env

load_backend_env()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.routers import (
    baidu_pan_sync, 
    config_memory, 
    content,
    creator,
    feishu_sync, 
    graph, 
    ip, 
    memory, 
    memory_consolidation, 
    multimodal, 
    style,
    vector
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS 配置 - 允许所有来源（解决跨域问题）
# 从环境变量读取，如果不设置则允许所有（开发环境方便调试）
cors_env = os.getenv("CORS_ORIGINS", "")
if cors_env:
    CORS_ORIGINS = [o.strip() for o in cors_env.split(",") if o.strip()]
else:
    # 默认允许的来源
    CORS_ORIGINS = [
        "https://ai-native-ip.netlify.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

# 如果设置 CORS_ALLOW_ALL=true，则允许所有来源（仅用于紧急调试）
if os.getenv("CORS_ALLOW_ALL", "").lower() in ("1", "true", "yes"):
    CORS_ORIGINS = ["*"]
    logger.info("CORS: 允许所有来源 (CORS_ALLOW_ALL=true)")
else:
    logger.info(f"CORS allowed origins: {CORS_ORIGINS}")


# 请求日志中间件
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"[Request] {request.method} {request.url.path} from {request.headers.get('origin', 'unknown')}")
        try:
            response = await call_next(request)
            logger.info(f"[Response] {request.method} {request.url.path} - {response.status_code}")
            return response
        except Exception as e:
            logger.exception(f"[Error] {request.method} {request.url.path} - {e}")
            raise


ROOT_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI-Native IP 工厂</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 2rem; background: #f5f5f5; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
    .card { background: #fff; border-radius: 12px; padding: 2.5rem; max-width: 480px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
    h1 { margin: 0 0 0.5rem; font-size: 1.5rem; color: #111; }
    .version { color: #666; font-size: 0.875rem; margin-bottom: 1.5rem; }
    p { color: #444; line-height: 1.6; margin: 0 0 1rem; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .links { margin-top: 1.5rem; }
    .links a { display: inline-block; margin-right: 1rem; margin-bottom: 0.5rem; }
    .note { font-size: 0.8125rem; color: #888; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #eee; }
  </style>
</head>
<body>
  <div class="card">
    <h1>AI-Native IP 工厂</h1>
    <p class="version">Phase 1 · 后端 API 服务</p>
    <p>当前为<strong>后端接口服务</strong>，提供 IP 管理、素材录入、Memory 配置等 API。配置中心产品前端正在规划中，上线后会提供完整操作界面。</p>
    <div class="links">
      <a href="/docs">→ API 文档（Swagger）</a><br />
      <a href="/redoc">→ API 文档（ReDoc）</a><br />
      <a href="/health">→ 健康检查</a>
    </div>
    <p class="note">第三方联调请使用 <code>/api/v1/</code> 前缀；创建 IP：POST /api/v1/ip，素材录入：POST /api/v1/memory/ingest。</p>
  </div>
</body>
</html>
"""


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI-Native IP Factory - Phase 1",
        version="0.1.0",
    )

    # 请求日志中间件（最先添加，记录所有请求）
    app.add_middleware(RequestLoggingMiddleware)

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    def root():
        return ROOT_HTML

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # Routers
    app.include_router(ip.router, prefix="/api/v1", tags=["ip"])
    app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
    app.include_router(config_memory.router, prefix="/api/v1", tags=["config"])
    app.include_router(feishu_sync.router, prefix="/api/v1", tags=["integrations"])
    app.include_router(baidu_pan_sync.router, prefix="/api/v1", tags=["integrations"])
    app.include_router(vector.router, prefix="/api/v1", tags=["vector"])
    app.include_router(graph.router, prefix="/api/v1", tags=["graph"])
    app.include_router(memory_consolidation.router, prefix="/api/v1", tags=["memory"])
    app.include_router(multimodal.router, prefix="/api/v1", tags=["multimodal"])
    app.include_router(content.router, prefix="/api/v1", tags=["content"])
    app.include_router(style.router, prefix="/api/v1", tags=["style"])
    app.include_router(creator.router, prefix="/api", tags=["creator"])

    return app


app = create_app()
