"""
AI-Native IP Factory - Phase 1 Backend
Simplified version for stability
"""
import os
import logging

# Worker service enabled - RQ queue processing

from app.env_loader import load_backend_env
load_backend_env()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.routers import (
    auth_sms,
    auth_email,
    baidu_pan_sync,
    config_memory,
    content,
    creator,
    debug,
    feishu_sync,
    graph,
    ip,
    memory,
    memory_consolidation,
    multimodal,
    strategy_agent,
    style,
    vector,
    remix,
    topic_recommendation,
)
from app.middleware.auth import verify_api_key_or_jwt

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS - 根据环境动态配置
is_production = os.getenv("RAILWAY_ENVIRONMENT_NAME") == "production"

if is_production:
    # 生产环境：只允许 Netlify 域名
    CORS_ORIGINS = [
        "https://ai-native-ip.netlify.app",
    ]
else:
    # 开发环境：允许本地
    CORS_ORIGINS = [
        "https://ai-native-ip.netlify.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

# 环境变量可以覆盖
cors_env = os.getenv("CORS_ORIGINS", "")
if cors_env:
    CORS_ORIGINS = [o.strip() for o in cors_env.split(",") if o.strip()]

logger.info(f"CORS origins: {CORS_ORIGINS}")

# Optional heavy router import: some local environments may lack torch DLLs.
# Keep core auth/login APIs available even when content-generation extras are unavailable.
try:
    from app.routers import content_generation
except Exception as e:
    content_generation = None
    logger.warning("content_generation router disabled: %s", e)

ROOT_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI-Native IP Factory</title>
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
    <h1>AI-Native IP Factory</h1>
    <p class="version">Phase 1 - Backend API</p>
    <p>Backend service for IP management and content generation.</p>
    <div class="links">
      <a href="/docs">API Docs (Swagger)</a><br />
      <a href="/health">Health Check</a>
    </div>
  </div>
</body>
</html>
"""

def create_app() -> FastAPI:
    app = FastAPI(
        title="AI-Native IP Factory",
        version="0.1.0",
    )

    # CORS middleware
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
        import inspect
        from app.services.ai_client import chat
        from app.config.ai_config import get_ai_config
        from app.services import tikhub_client

        cfg = get_ai_config()
        sig = inspect.signature(chat)
        return {
            "status": "ok",
            "git_sha": os.getenv("RAILWAY_GIT_COMMIT_SHA")
            or os.getenv("RAILWAY_GIT_SHA")
            or os.getenv("GIT_SHA")
            or "",
            "llm_available": bool(cfg.get("llm_available")),
            "has_api_key": bool(cfg.get("api_key")),
            "llm_model": cfg.get("llm_model") or "",
            "chat_supports_temperature": "temperature" in sig.parameters,
            "tikhub_configured": tikhub_client.is_configured(),
            "tikhub_api_key_preview": os.getenv("TIKHUB_API_KEY", "")[:10] + "..." if os.getenv("TIKHUB_API_KEY") else "NOT_SET",
        }

    # API Key 或用户 JWT（发码/登录见 auth 路由，无需此依赖）
    api_key_dep = [Depends(verify_api_key_or_jwt)]

    app.include_router(auth_sms.router, prefix="/api/auth", tags=["auth"])
    app.include_router(auth_email.router, prefix="/api/auth", tags=["auth"])

    # API routes - 需要认证
    app.include_router(ip.router, prefix="/api/v1", tags=["ip"], dependencies=api_key_dep)
    app.include_router(memory.router, prefix="/api/v1", tags=["memory"], dependencies=api_key_dep)
    app.include_router(config_memory.router, prefix="/api/v1", tags=["config"], dependencies=api_key_dep)
    app.include_router(feishu_sync.router, prefix="/api/v1", tags=["integrations"], dependencies=api_key_dep)
    app.include_router(baidu_pan_sync.router, prefix="/api/v1", tags=["integrations"], dependencies=api_key_dep)
    app.include_router(vector.router, prefix="/api/v1", tags=["vector"], dependencies=api_key_dep)
    app.include_router(graph.router, prefix="/api/v1", tags=["graph"], dependencies=api_key_dep)
    app.include_router(memory_consolidation.router, prefix="/api/v1", tags=["memory"], dependencies=api_key_dep)
    app.include_router(multimodal.router, prefix="/api/v1", tags=["multimodal"], dependencies=api_key_dep)
    app.include_router(content.router, prefix="/api/v1", tags=["content"], dependencies=api_key_dep)
    if content_generation is not None:
        app.include_router(
            content_generation.router, prefix="/api/v1", tags=["content-generation"], dependencies=api_key_dep
        )
    app.include_router(strategy_agent.router, prefix="/api/v1", tags=["strategy"], dependencies=api_key_dep)
    app.include_router(style.router, prefix="/api/v1", tags=["style"], dependencies=api_key_dep)
    app.include_router(remix.router, prefix="/api/v1", tags=["remix"], dependencies=api_key_dep)
    app.include_router(topic_recommendation.router, prefix="/api/v1", tags=["topic"], dependencies=api_key_dep)
    app.include_router(debug.router, prefix="/api/v1", tags=["debug"], dependencies=api_key_dep)
    # Creator 路由 - 推荐选题等接口公开访问
    app.include_router(creator.router, prefix="/api/v1", tags=["creator"])

    return app

app = create_app()
