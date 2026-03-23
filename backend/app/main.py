"""
AI-Native IP Factory - Phase 1 Backend
Simplified version for stability
"""
import os
import logging

from app.env_loader import load_backend_env
load_backend_env()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS - Allow Netlify frontend
CORS_ORIGINS = [
    "https://ai-native-ip.netlify.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Override from environment if set
cors_env = os.getenv("CORS_ORIGINS", "")
if cors_env:
    CORS_ORIGINS = [o.strip() for o in cors_env.split(",") if o.strip()]

logger.info(f"CORS origins: {CORS_ORIGINS}")

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
        return {"status": "ok"}

    # API routes
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
