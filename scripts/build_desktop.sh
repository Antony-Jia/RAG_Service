#!/usr/bin/env bash
set -euo pipefail

echo "[build] Building admin ui..."
(
  cd apps/kb_admin_ui
  npm run build
)

echo "[build] Copying UI build -> daemon static"
rm -rf apps/kb_desktop_daemon/src/kb_desktop_daemon/static
cp -r apps/kb_admin_ui/build apps/kb_desktop_daemon/src/kb_desktop_daemon/static

echo "[build] Packaging daemon exe (placeholder)"
echo "Run: pyinstaller -y apps/kb_desktop_daemon/build/pyinstaller.spec"
