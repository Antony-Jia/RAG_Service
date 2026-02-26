from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MetadataFilter(BaseModel):
    equals: dict[str, Any] = Field(default_factory=dict)


class VectorItem(BaseModel):
    id: str
    vector: list[float]
    collection_id: str
    document_id: str
    chunk_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorHit(BaseModel):
    id: str
    score: float
    collection_id: str
    document_id: str
    chunk_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
