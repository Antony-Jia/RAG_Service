from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from kb_core.models import Collection, IngestOptions, Job, JobStatus, JobType, MetadataFilter
from kb_core.pipelines import delete_document, ingest_document, retrieve

from kb_desktop_daemon.http.auth import require_auth
from kb_desktop_daemon.http.schemas import (
    CapabilitiesResponse,
    CreateCollectionRequest,
    DeleteResponse,
    IngestResponse,
    RetrieveRequest,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


def build_api_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_auth)])

    @router.get("/capabilities", response_model=CapabilitiesResponse)
    def capabilities() -> CapabilitiesResponse:
        return CapabilitiesResponse(
            parsers=["text", "pdf", "docx"],
            providers={
                "llm": ["ollama", "open_compat"],
                "embedding": ["ollama", "open_compat"],
            },
            features={
                "retrieve": True,
                "ingest_upload": True,
                "metadata_filter_equals": True,
            },
        )

    @router.post("/collections")
    def create_collection(payload: CreateCollectionRequest, request: Request) -> dict[str, Any]:
        ctx = request.app.state.ctx
        collection = Collection(
            name=payload.name,
            description=payload.description,
            settings=payload.settings,
        )
        created = ctx.repo.create_collection(collection)
        return created.model_dump()

    @router.get("/collections")
    def list_collections(
        request: Request,
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, Any]]:
        ctx = request.app.state.ctx
        return [c.model_dump() for c in ctx.repo.list_collections(limit=limit, offset=offset)]

    @router.get("/collections/{collection_id}")
    def get_collection(collection_id: str, request: Request) -> dict[str, Any]:
        ctx = request.app.state.ctx
        collection = ctx.repo.get_collection(collection_id)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")
        return collection.model_dump()

    @router.delete("/collections/{collection_id}")
    def delete_collection(collection_id: str, request: Request) -> dict[str, bool]:
        ctx = request.app.state.ctx
        ctx.repo.delete_collection(collection_id)
        return {"ok": True}

    @router.post("/ingest/upload", response_model=IngestResponse)
    async def ingest_upload(
        request: Request,
        file: UploadFile = File(...),
        collection_id: str = Form(...),
        options: str = Form(default="{}"),
    ) -> IngestResponse:
        ctx = request.app.state.ctx
        collection = ctx.repo.get_collection(collection_id)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collection not found")

        try:
            parsed_opts = json.loads(options)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid options JSON: {exc}") from exc

        data = await file.read()
        document_id = str(uuid4())
        ingest_options = IngestOptions(
            chunk_size=int(parsed_opts.get("chunk_size", ctx.settings.chunk_size)),
            chunk_overlap=int(parsed_opts.get("chunk_overlap", ctx.settings.chunk_overlap)),
            parser_name=parsed_opts.get("parser_name"),
            metadata=parsed_opts.get("metadata", {}),
        )

        job = Job(
            type=JobType.INGEST,
            status=JobStatus.QUEUED,
            payload={
                "collection_id": collection_id,
                "document_id": document_id,
                "filename": file.filename,
            },
            created_at=utcnow(),
        )
        ctx.repo.create_job(job)

        def _task() -> None:
            ctx.repo.update_job(job.id, progress=30)
            ingest_document(
                collection_id=collection_id,
                filename=file.filename or "upload.bin",
                mime=file.content_type or "application/octet-stream",
                content=data,
                blob_store=ctx.blob_store,
                document_store=ctx.repo,
                chunk_store=ctx.repo,
                vector_index=ctx.vector_index,
                embedder=ctx.embedder,
                parsers=ctx.parsers,
                options=ingest_options,
                document_id=document_id,
            )
            ctx.repo.update_job(job.id, progress=90)

        ctx.worker.submit(job.id, _task)
        return IngestResponse(job_id=job.id, document_id=document_id)

    @router.post("/retrieve")
    def retrieve_api(payload: RetrieveRequest, request: Request) -> dict[str, Any]:
        ctx = request.app.state.ctx
        filter_obj = MetadataFilter(equals=payload.filters or {}) if payload.filters else None
        top_k = payload.top_k or ctx.settings.retrieve_top_k

        result = retrieve(
            query=payload.query,
            collection_ids=payload.collection_ids,
            top_k=top_k,
            include_chunks=payload.include_chunks,
            filters=filter_obj,
            embedder=ctx.embedder,
            vector_index=ctx.vector_index,
            chunk_store=ctx.repo,
            document_store=ctx.repo,
        )
        return result.model_dump()

    @router.delete("/documents/{document_id}", response_model=DeleteResponse)
    def delete_document_api(document_id: str, request: Request) -> DeleteResponse:
        ctx = request.app.state.ctx
        document = ctx.repo.get_document(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")

        job = Job(
            type=JobType.DELETE,
            status=JobStatus.QUEUED,
            payload={"document_id": document_id, "collection_id": document.collection_id},
            created_at=utcnow(),
        )
        ctx.repo.create_job(job)

        def _task() -> None:
            delete_document(
                collection_id=document.collection_id,
                document_id=document_id,
                document_store=ctx.repo,
                chunk_store=ctx.repo,
                vector_index=ctx.vector_index,
            )

        ctx.worker.submit(job.id, _task)
        return DeleteResponse(job_id=job.id)

    @router.get("/jobs")
    def list_jobs(
        request: Request,
        status: JobStatus | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict[str, Any]]:
        ctx = request.app.state.ctx
        jobs = ctx.repo.list_jobs(limit=limit, offset=offset, status=status)
        return [job.model_dump() for job in jobs]

    @router.get("/jobs/{job_id}")
    def get_job(job_id: str, request: Request) -> dict[str, Any]:
        ctx = request.app.state.ctx
        job = ctx.repo.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job.model_dump()

    return router
