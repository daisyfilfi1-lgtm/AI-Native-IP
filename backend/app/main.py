from fastapi import FastAPI

from app.routers import config_memory, ip, memory


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI-Native IP Factory - Phase 1",
        version="0.1.0",
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # Routers
    app.include_router(ip.router, prefix="/api/v1", tags=["ip"])
    app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
    app.include_router(config_memory.router, prefix="/api/v1", tags=["config"])

    return app


app = create_app()

