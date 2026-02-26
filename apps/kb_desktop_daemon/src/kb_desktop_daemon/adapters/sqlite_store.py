from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any

from kb_core.models import Chunk, Collection, Document, Job, JobStatus, JobType


class SQLiteRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    settings_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_uri TEXT,
                    mime TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    hash TEXT,
                    blob_ref TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    token_count INTEGER,
                    chunk_order INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    embedding_ref TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    message TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS chunk_vector_map (
                    chunk_id TEXT PRIMARY KEY,
                    collection_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    vector_id TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_documents_collection ON documents(collection_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
                CREATE INDEX IF NOT EXISTS idx_vector_doc ON chunk_vector_map(document_id);
                """
            )
            conn.commit()

    @staticmethod
    def _dumps(value: dict[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=True)

    @staticmethod
    def _loads(value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        return json.loads(value)

    @staticmethod
    def _dt(value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    def create_collection(self, collection: Collection) -> Collection:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO collections(id, name, description, settings_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    collection.id,
                    collection.name,
                    collection.description,
                    self._dumps(collection.settings),
                    collection.created_at.isoformat(),
                    collection.updated_at.isoformat(),
                ),
            )
            conn.commit()
        return collection

    def get_collection(self, collection_id: str) -> Collection | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,)).fetchone()
            if row is None:
                return None
            return Collection(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                settings=self._loads(row["settings_json"]),
                created_at=self._dt(row["created_at"]),
                updated_at=self._dt(row["updated_at"]),
            )

    def list_collections(self, limit: int, offset: int) -> list[Collection]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM collections ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [
                Collection(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    settings=self._loads(row["settings_json"]),
                    created_at=self._dt(row["created_at"]),
                    updated_at=self._dt(row["updated_at"]),
                )
                for row in rows
            ]

    def delete_collection(self, collection_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
            conn.commit()

    def create_document(self, doc: Document) -> Document:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents(
                    id, collection_id, title, source_type, source_uri, mime, size_bytes,
                    hash, blob_ref, status, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.id,
                    doc.collection_id,
                    doc.title,
                    doc.source_type,
                    doc.source_uri,
                    doc.mime,
                    doc.size_bytes,
                    doc.hash,
                    doc.blob_ref,
                    doc.status.value,
                    self._dumps(doc.metadata),
                    doc.created_at.isoformat(),
                    doc.updated_at.isoformat(),
                ),
            )
            conn.commit()
        return doc

    def get_document(self, document_id: str) -> Document | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            if row is None:
                return None
            return Document(
                id=row["id"],
                collection_id=row["collection_id"],
                title=row["title"],
                source_type=row["source_type"],
                source_uri=row["source_uri"],
                mime=row["mime"],
                size_bytes=row["size_bytes"],
                hash=row["hash"],
                blob_ref=row["blob_ref"],
                status=row["status"],
                metadata=self._loads(row["metadata_json"]),
                created_at=self._dt(row["created_at"]),
                updated_at=self._dt(row["updated_at"]),
            )

    def list_documents(self, collection_id: str, limit: int, offset: int) -> list[Document]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM documents
                WHERE collection_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (collection_id, limit, offset),
            ).fetchall()
            return [
                Document(
                    id=row["id"],
                    collection_id=row["collection_id"],
                    title=row["title"],
                    source_type=row["source_type"],
                    source_uri=row["source_uri"],
                    mime=row["mime"],
                    size_bytes=row["size_bytes"],
                    hash=row["hash"],
                    blob_ref=row["blob_ref"],
                    status=row["status"],
                    metadata=self._loads(row["metadata_json"]),
                    created_at=self._dt(row["created_at"]),
                    updated_at=self._dt(row["updated_at"]),
                )
                for row in rows
            ]

    def update_document(self, doc: Document) -> Document:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE documents
                SET title = ?, source_type = ?, source_uri = ?, mime = ?, size_bytes = ?, hash = ?,
                    blob_ref = ?, status = ?, metadata_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    doc.title,
                    doc.source_type,
                    doc.source_uri,
                    doc.mime,
                    doc.size_bytes,
                    doc.hash,
                    doc.blob_ref,
                    doc.status.value,
                    self._dumps(doc.metadata),
                    doc.updated_at.isoformat(),
                    doc.id,
                ),
            )
            conn.commit()
        return doc

    def delete_document(self, document_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            conn.commit()

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        with self._lock, self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO chunks(
                    id, collection_id, document_id, text, token_count,
                    chunk_order, metadata_json, embedding_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    text = excluded.text,
                    token_count = excluded.token_count,
                    chunk_order = excluded.chunk_order,
                    metadata_json = excluded.metadata_json,
                    embedding_ref = excluded.embedding_ref
                """,
                [
                    (
                        chunk.id,
                        chunk.collection_id,
                        chunk.document_id,
                        chunk.text,
                        chunk.token_count,
                        chunk.order,
                        self._dumps(chunk.metadata),
                        chunk.embedding_ref,
                        chunk.created_at.isoformat(),
                    )
                    for chunk in chunks
                ],
            )
            conn.commit()

    def get_chunks(self, chunk_ids: list[str]) -> list[Chunk]:
        if not chunk_ids:
            return []
        placeholders = ",".join("?" for _ in chunk_ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM chunks WHERE id IN ({placeholders})",
                tuple(chunk_ids),
            ).fetchall()
        return [
            Chunk(
                id=row["id"],
                collection_id=row["collection_id"],
                document_id=row["document_id"],
                text=row["text"],
                token_count=row["token_count"],
                order=row["chunk_order"],
                metadata=self._loads(row["metadata_json"]),
                embedding_ref=row["embedding_ref"],
                created_at=self._dt(row["created_at"]),
            )
            for row in rows
        ]

    def delete_chunks_by_document(self, document_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            conn.commit()

    def create_job(self, job: Job) -> Job:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs(id, type, status, progress, message, payload_json, created_at, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.type.value,
                    job.status.value,
                    job.progress,
                    job.message,
                    self._dumps(job.payload),
                    job.created_at.isoformat(),
                    job.started_at.isoformat() if job.started_at else None,
                    job.finished_at.isoformat() if job.finished_at else None,
                ),
            )
            conn.commit()
        return job

    def get_job(self, job_id: str) -> Job | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None:
                return None
            return Job(
                id=row["id"],
                type=row["type"],
                status=row["status"],
                progress=row["progress"],
                message=row["message"],
                payload=self._loads(row["payload_json"]),
                created_at=self._dt(row["created_at"]),
                started_at=self._dt(row["started_at"]),
                finished_at=self._dt(row["finished_at"]),
            )

    def list_jobs(self, limit: int, offset: int, status: JobStatus | None = None) -> list[Job]:
        sql = "SELECT * FROM jobs"
        params: list[Any] = []
        if status is not None:
            sql += " WHERE status = ?"
            params.append(status.value)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        return [
            Job(
                id=row["id"],
                type=row["type"],
                status=row["status"],
                progress=row["progress"],
                message=row["message"],
                payload=self._loads(row["payload_json"]),
                created_at=self._dt(row["created_at"]),
                started_at=self._dt(row["started_at"]),
                finished_at=self._dt(row["finished_at"]),
            )
            for row in rows
        ]

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
        payload: dict | None = None,
        job_type: JobType | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> Job:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f"Job not found: {job_id}")

        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if message is not None:
            job.message = message
        if payload is not None:
            job.payload = payload
        if job_type is not None:
            job.type = job_type
        if started_at is not None:
            job.started_at = started_at
        if finished_at is not None:
            job.finished_at = finished_at

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET type = ?, status = ?, progress = ?, message = ?, payload_json = ?, started_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (
                    job.type.value,
                    job.status.value,
                    job.progress,
                    job.message,
                    self._dumps(job.payload),
                    job.started_at.isoformat() if job.started_at else None,
                    job.finished_at.isoformat() if job.finished_at else None,
                    job.id,
                ),
            )
            conn.commit()
        return job

    def upsert_chunk_vector_map(
        self,
        *,
        chunk_id: str,
        collection_id: str,
        document_id: str,
        vector_id: str,
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chunk_vector_map(chunk_id, collection_id, document_id, vector_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    collection_id = excluded.collection_id,
                    document_id = excluded.document_id,
                    vector_id = excluded.vector_id
                """,
                (chunk_id, collection_id, document_id, vector_id),
            )
            conn.commit()

    def delete_chunk_vector_map_by_document(self, document_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM chunk_vector_map WHERE document_id = ?", (document_id,))
            conn.commit()
