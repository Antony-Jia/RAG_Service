from __future__ import annotations

from pydantic import BaseModel, Field


class CreateCollectionRequest(BaseModel):
    name: str
    description: str | None = None
    settings: dict = Field(default_factory=dict)


class RetrieveRequest(BaseModel):
    query: str
    collection_ids: list[str]
    top_k: int = 10
    filters: dict | None = None
    include_chunks: bool = True


class IngestResponse(BaseModel):
    job_id: str
    document_id: str


class DeleteResponse(BaseModel):
    job_id: str


class CapabilitiesResponse(BaseModel):
    parsers: list[str]
    providers: dict
    features: dict
