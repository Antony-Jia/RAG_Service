# kb_server

This package is intentionally a runnable skeleton.

## Implemented
- FastAPI app with `/healthz` and `/api/v1/capabilities`.
- Adapter placeholders for Postgres and pgvector.
- Reuses `kb_core` package boundaries.

## TODO (next phase)
- Multi-tenant auth middleware and tenant-aware storage.
- SQL migrations and production deployment manifests.
- Async job queue integration.
- Full parity with desktop host API.
