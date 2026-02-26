from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from kb_desktop_daemon.adapters import (
    ChromaVectorIndex,
    LocalBlobStore,
    ProviderFactory,
    SQLiteRepository,
    default_parsers,
)
from kb_desktop_daemon.config import Settings
from kb_desktop_daemon.http.api import build_api_router
from kb_desktop_daemon.http.context import AppContext
from kb_desktop_daemon.http.worker import JobWorker


def create_app(settings: Settings | None = None, auth_token: str | None = None) -> FastAPI:
    cfg = settings or Settings()
    cfg.ensure_dirs()
    token = auth_token or cfg.resolved_auth_token()

    repo = SQLiteRepository(str(cfg.sqlite_path))
    provider_factory = ProviderFactory(cfg)
    embedder = provider_factory.create_embedder()
    llm_client = provider_factory.create_llm_client()

    ctx = AppContext(
        settings=cfg,
        auth_token=token,
        repo=repo,
        vector_index=ChromaVectorIndex(str(cfg.chroma_path), repo=repo),
        blob_store=LocalBlobStore(str(cfg.blob_path)),
        embedder=embedder,
        llm_client=llm_client,
        parsers=default_parsers(),
        worker=JobWorker(repo=repo),
    )

    app = FastAPI(title="KB Desktop Daemon", version="0.1.0")
    app.state.ctx = ctx
    app.include_router(build_api_router())

    @app.on_event("startup")
    def on_startup() -> None:
        app.state.ctx.worker.start()

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        app.state.ctx.worker.stop()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/session")
    def session(request: Request) -> dict[str, str]:
        client = request.client.host if request.client else ""
        if client not in {"127.0.0.1", "::1", "localhost"}:
            raise HTTPException(status_code=403, detail="Forbidden")
        return {"token": app.state.ctx.auth_token}

    static_dir = Path(__file__).resolve().parent.parent / "static"

    @app.get("/{path:path}", response_model=None)
    def static_handler(path: str):
        if path.startswith("api/") or path == "healthz":
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        candidate = static_dir / path
        if path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)

        index_file = static_dir / "index.html"
        if not index_file.exists():
            return JSONResponse(status_code=404, content={"detail": "UI build not found"})
        return FileResponse(index_file)

    return app
