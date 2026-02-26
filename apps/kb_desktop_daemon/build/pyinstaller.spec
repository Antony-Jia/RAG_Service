# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for kb-desktop-daemon.

Build (run from project root):
    pyinstaller -y apps/kb_desktop_daemon/build/pyinstaller.spec

Prerequisites:
    pip install pyinstaller           # install PyInstaller (>=5.0)
    scripts/build_desktop.ps1         # build UI and copy static files first

Output:
    dist/kb-desktop-daemon/           (onedir bundle)
    dist/kb-desktop-daemon/kb-desktop-daemon.exe
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ---------------------------------------------------------------------------
# Path resolution
#   SPECPATH is provided by PyInstaller and equals the directory of this file:
#     apps/kb_desktop_daemon/build/
# ---------------------------------------------------------------------------
SPEC_DIR = Path(SPECPATH)
DAEMON_ROOT = (SPEC_DIR / "..").resolve()          # apps/kb_desktop_daemon/
PROJECT_ROOT = (SPEC_DIR / "../../..").resolve()   # repo root (RAG_Service/)

SRC_DIR = DAEMON_ROOT / "src"
KB_CORE_SRC = PROJECT_ROOT / "packages" / "kb_core" / "src"

STATIC_DIR = SRC_DIR / "kb_desktop_daemon" / "static"

# ---------------------------------------------------------------------------
# Data files
#   chromadb embeds migration SQL and other resources that must travel with it.
#   python-docx embeds a default.docx template.
#   The compiled React UI lives in static/ and is resolved at runtime via
#     Path(__file__).parent.parent / "static"   (see http/app.py)
# ---------------------------------------------------------------------------
datas = (
    collect_data_files("chromadb")
    + collect_data_files("docx")
)

if STATIC_DIR.exists():
    datas.append((str(STATIC_DIR), "kb_desktop_daemon/static"))

# ---------------------------------------------------------------------------
# Hidden imports
#   uvicorn, chromadb, and pydantic use importlib/string-based loading that
#   the static analyser cannot follow automatically.
# ---------------------------------------------------------------------------
hidden_imports = collect_submodules("chromadb") + [
    # uvicorn – event loop and protocol implementations are loaded by name
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    # starlette
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.routing",
    # pydantic / pydantic-settings
    "pydantic",
    "pydantic.deprecated.class_validators",
    "pydantic_settings",
    # document parsers
    "pypdf",
    "docx",
    "multipart",
    # local workspace packages
    "kb_core",
    "kb_core.models",
    "kb_core.ports",
    "kb_core.pipelines",
    "kb_core.services",
    "kb_core.errors",
    "kb_desktop_daemon",
    "kb_desktop_daemon.config",
    "kb_desktop_daemon.adapters",
    "kb_desktop_daemon.http",
]

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(SRC_DIR / "kb_desktop_daemon" / "main.py")],
    pathex=[str(SRC_DIR), str(KB_CORE_SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# ---------------------------------------------------------------------------
# Executable
#   console=True  – daemon writes JSON to stdout on startup (see main.py)
#   upx=False     – avoids potential AV false-positives on Windows
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="kb-desktop-daemon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ---------------------------------------------------------------------------
# One-dir bundle
#   Using onedir (vs onefile) for faster startup and simpler static file
#   resolution at runtime.
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="kb-desktop-daemon",
)
