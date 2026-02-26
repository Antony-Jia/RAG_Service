#!/usr/bin/env bash
set -euo pipefail

echo "[dev] Starting desktop daemon (python) and admin ui (vite)..."
echo "1) uv sync --all-packages --group dev"
echo "2) cd apps/kb_admin_ui && npm install && npm run dev"
echo "3) uv run --package kb-desktop-daemon kb-desktop-daemon"
