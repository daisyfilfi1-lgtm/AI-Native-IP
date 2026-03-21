import os

from app.env_loader import load_backend_env

load_backend_env()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.routers import (
    baidu_pan_sync, 
    config_memory, 
    content,
    feishu_sync, 
    graph, 
    ip, 
    memory, 
    memory_consolidation, 
    multimodal, 
    style,
    vector
)

# 未设置 CORS_ORIGINS 时：允许 Netlify 正式/预览域名与本地开发（比单纯 * 更明确，便于排查）
_DEFAULT_NETLIFY_LOCAL_REGEX = (
    r"^https://[^/]+\.netlify\.app$"  # 含 deploy-preview-xxx--repo.netlify.app
    r"|^http://localhost(?::\d+)?$"
)


def _cors_middleware_kwargs() -> dict:
    """
    浏览器禁止同时使用 Access-Control-Allow-Origin: * 与 Allow-Credentials: true。
    原配置 allow_origins=['*'] + allow_credentials=True 会导致跨域（含直连 Railway）被拦截。

    说明：若网关返回 502（应用未响应），响应不经过本中间件，浏览器会报「无 CORS 头」——
    根因多为上游故障/超时，需先修部署稳定性；成功响应时本配置才会带上 CORS。
    """
    cred = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() in ("1", "true", "yes")
    regex = os.getenv("CORS_ORIGIN_REGEX", "").strip() or None
    raw_env = os.getenv("CORS_ORIGINS")
    if regex:
        return {
            "allow_origin_regex": regex,
            "allow_credentials": cred,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
    if raw_env is None:
        return {
            "allow_origin_regex": _DEFAULT_NETLIFY_LOCAL_REGEX,
            "allow_credentials": False,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
    raw = raw_env.strip()
    if not raw or raw == "*":
        return {
            "allow_origins": ["*"],
            "allow_credentials": False,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not origins:
        return {
            "allow_origins": ["*"],
            "allow_credentials": False,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
    return {
        "allow_origins": origins,
        "allow_credentials": cred,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }


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

    app.add_middleware(CORSMiddleware, **_cors_middleware_kwargs())

    @app.get("/", response_class=HTMLResponse)
    def root():
        """产品欢迎页：说明当前为后端服务，并引导到 API 文档。"""
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

    return app


app = create_app()

