from __future__ import annotations

import secrets
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_host: str = "127.0.0.1"
    app_port: int = 0
    app_data_dir: str = "./data"
    auth_token: str | None = None

    llm_provider: str = "ollama"
    embedding_provider: str = "ollama"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_llm_model: str = "qwen2.5:7b-instruct"
    ollama_embed_model: str = "nomic-embed-text"

    open_compat_base_url: str = "https://api.openai.com/v1"
    open_compat_api_key: str = "YOUR_KEY"
    open_compat_llm_model: str = "gpt-4o-mini"
    open_compat_embed_model: str = "text-embedding-3-small"

    retrieve_top_k: int = 10
    chunk_size: int = 800
    chunk_overlap: int = 120

    daemon_state_dir: str = Field(default="~/.openanywork/kb")

    @property
    def data_dir(self) -> Path:
        return Path(self.app_data_dir).resolve()

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "kb.sqlite3"

    @property
    def chroma_path(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def blob_path(self) -> Path:
        return self.data_dir / "blobs"

    @property
    def daemon_state_path(self) -> Path:
        return Path(self.daemon_state_dir).expanduser() / "daemon.json"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.blob_path.mkdir(parents=True, exist_ok=True)
        self.daemon_state_path.parent.mkdir(parents=True, exist_ok=True)

    def resolved_auth_token(self) -> str:
        return self.auth_token or secrets.token_urlsafe(32)
