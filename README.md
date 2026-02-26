# RAG Service Monorepo

Monorepo for a reusable Python knowledge base engine (`kb_core`) with two host apps:
- `kb_desktop_daemon`: complete local runnable host (SQLite + ChromaDB + local API + static UI)
- `kb_server`: runnable skeleton for future Postgres + pgvector deployment

## Layout
- `packages/kb_core`: models, ports, pipelines, services
- `apps/kb_desktop_daemon`: FastAPI daemon + adapters + job worker + static hosting
- `apps/kb_admin_ui`: React/Vite admin UI
- `apps/kb_server`: server skeleton
- `integrations/openanywork_plugin`: plugin integration examples
- `shared/openapi`: API contract draft

## Quick Start
1. `uv sync --all-packages --group dev`
2. Optional UI dev:
   - `cd apps/kb_admin_ui`
   - `npm install`
   - `npm run dev`
3. Run desktop daemon:
   - `uv run --package kb-desktop-daemon kb-desktop-daemon`

Daemon prints runtime JSON on stdout:
```json
{"port": 51743, "token": "...", "base_url": "http://127.0.0.1:51743"}
```
Also persisted to `~/.openanywork/kb/daemon.json`.

## Auth
All `/api/*` routes require:
- `Authorization: Bearer <token>`

## Environment
Copy `.env.example` to `.env` and adjust providers:
- `LLM_PROVIDER=ollama|open_compat`
- `EMBEDDING_PROVIDER=ollama|open_compat`

## Build Desktop
- `scripts/build_desktop.ps1` (Windows)
- `scripts/build_desktop.sh` (Unix)

Build flow:
1. Build `kb_admin_ui`
2. Copy build artifacts to daemon `static/`
3. Package daemon executable via PyInstaller (placeholder spec included)

## Test
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy packages apps`

## Status
- Desktop path is implemented for MVP ingest/retrieve/job flow.
- Server path is intentionally scaffolded with TODO adapters for Postgres/pgvector, auth, tenants, and queueing.
