param()

$ErrorActionPreference = "Stop"

Write-Host "[build] Building admin ui..."
Push-Location apps/kb_admin_ui
npm run build
Pop-Location

Write-Host "[build] Copying UI build -> daemon static"
$source = "apps/kb_admin_ui/build"
$target = "apps/kb_desktop_daemon/src/kb_desktop_daemon/static"
if (Test-Path $target) { Remove-Item -Recurse -Force $target }
Copy-Item -Recurse -Force $source $target

Write-Host "[build] Packaging daemon exe (placeholder)"
Write-Host "Run: pyinstaller -y apps/kb_desktop_daemon/build/pyinstaller.spec"
