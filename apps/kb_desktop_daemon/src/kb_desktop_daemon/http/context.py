from __future__ import annotations

from dataclasses import dataclass

from kb_core.ports import Embedder, LLMClient

from kb_desktop_daemon.adapters import ChromaVectorIndex, LocalBlobStore, SQLiteRepository
from kb_desktop_daemon.config import Settings
from kb_desktop_daemon.http.worker import JobWorker


@dataclass
class AppContext:
    settings: Settings
    auth_token: str
    repo: SQLiteRepository
    vector_index: ChromaVectorIndex
    blob_store: LocalBlobStore
    embedder: Embedder
    llm_client: LLMClient
    parsers: list[object]
    worker: JobWorker
