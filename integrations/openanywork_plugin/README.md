# OpenAnyWork Plugin Integration (Example)

This folder provides a minimal TypeScript example for integrating with `kb_desktop_daemon`.

## Flow
1. Spawn local daemon executable.
2. Read first stdout line JSON: `{ port, token, base_url }`.
3. Call `/api/v1/*` with `Authorization: Bearer <token>`.

## Notes
- Keep daemon bound to `127.0.0.1` only.
- Persist process handle for graceful shutdown.
- You can point Electron WebView to `base_url`.
