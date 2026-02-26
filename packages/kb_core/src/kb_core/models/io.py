from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BlobRef(BaseModel):
    id: str
    path: str
    name: str
    mime: str


class ParseOptions(BaseModel):
    language: str | None = None
    parser_name: str | None = None
    extras: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestOptions(BaseModel):
    chunk_size: int = 800
    chunk_overlap: int = 120
    parser_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
