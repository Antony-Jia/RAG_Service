from __future__ import annotations

import json
import socket
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from kb_desktop_daemon.config import Settings
from kb_desktop_daemon.http import create_app


def _find_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _write_daemon_state(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def main() -> None:
    load_dotenv()
    settings = Settings()
    settings.ensure_dirs()

    token = settings.resolved_auth_token()
    port = settings.app_port if settings.app_port > 0 else _find_free_port(settings.app_host)
    base_url = f"http://{settings.app_host}:{port}"

    runtime_info = {
        "port": port,
        "token": token,
        "base_url": base_url,
    }
    _write_daemon_state(settings.daemon_state_path, runtime_info)
    print(json.dumps(runtime_info, ensure_ascii=True), flush=True)

    app = create_app(settings=settings, auth_token=token)
    uvicorn.run(app, host=settings.app_host, port=port)


if __name__ == "__main__":
    main()
