from __future__ import annotations

from fastapi import FastAPI

from kb_server.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()

    app = FastAPI(title="KB Server (Skeleton)", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/capabilities")
    def capabilities() -> dict:
        return {
            "mode": "skeleton",
            "stores": ["postgres(todo)", "pgvector(todo)"],
            "auth": cfg.auth_mode,
            "tenancy": cfg.tenant_mode,
        }

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "kb_server skeleton is running"}

    return app
