from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class DocumentStatus(str, Enum):
    PENDING = "pending"
    INGESTED = "ingested"
    FAILED = "failed"
    DELETED = "deleted"


class JobType(str, Enum):
    INGEST = "INGEST"
    DELETE = "DELETE"
    REINDEX = "REINDEX"


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Collection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    collection_id: str
    title: str
    source_type: str = "upload"
    source_uri: str | None = None
    mime: str
    size_bytes: int
    hash: str | None = None
    blob_ref: str
    status: DocumentStatus = DocumentStatus.PENDING
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    collection_id: str
    document_id: str
    text: str
    token_count: int | None = None
    order: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding_ref: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class Citation(BaseModel):
    document_id: str
    chunk_id: str
    snippet: str
    page: int | None = None
    start_char: int | None = None
    end_char: int | None = None


class RetrieveHit(BaseModel):
    chunk_id: str
    score: float
    text: str | None = None
    citation: Citation
    document: dict[str, Any]


class RetrieveResult(BaseModel):
    query: str
    hits: list[RetrieveHit]


class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: JobType
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
