param()

Write-Host "[dev] Starting desktop daemon (python) and admin ui (vite)..."
Write-Host "1) uv sync --all-packages --group dev"
Write-Host "2) cd apps/kb_admin_ui; npm install; npm run dev"
Write-Host "3) uv run --package kb-desktop-daemon kb-desktop-daemon"
