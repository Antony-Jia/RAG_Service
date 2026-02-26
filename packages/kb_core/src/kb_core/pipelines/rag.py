from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from kb_core.errors import ParserNotFoundError
from kb_core.models import (
    BlobRef,
    Chunk,
    Citation,
    Document,
    DocumentStatus,
    IngestOptions,
    MetadataFilter,
    ParseOptions,
    RetrieveHit,
    RetrieveResult,
    VectorItem,
)
from kb_core.ports import BlobStore, ChunkStore, DocumentStore, Embedder, Parser, VectorIndex
from kb_core.services import chunk_text, estimate_token_count, match_metadata


def _select_parser(parsers: Iterable[Parser], mime: str, filename: str, parser_name: str | None = None) -> Parser:
    ext = Path(filename).suffix.lower()
    for parser in parsers:
        if parser.can_parse(mime, ext):
            return parser
    raise ParserNotFoundError(f"No parser matched mime={mime}, ext={ext}, parser_name={parser_name}")


def ingest_document(
    *,
    collection_id: str,
    filename: str,
    mime: str,
    content: bytes,
    blob_store: BlobStore,
    document_store: DocumentStore,
    chunk_store: ChunkStore,
    vector_index: VectorIndex,
    embedder: Embedder,
    parsers: Iterable[Parser],
    options: IngestOptions,
    document_id: str | None = None,
) -> Document:
    parser = _select_parser(parsers, mime=mime, filename=filename, parser_name=options.parser_name)
    content_hash = sha256(content).hexdigest()

    blob_ref: BlobRef = blob_store.put(content, name=filename, mime=mime)

    document = Document(
        id=document_id or str(uuid4()),
        collection_id=collection_id,
        title=filename,
        source_type="upload",
        mime=mime,
        size_bytes=len(content),
        hash=content_hash,
        blob_ref=blob_ref.path,
        status=DocumentStatus.PENDING,
        metadata=options.metadata,
    )
    document_store.create_document(document)

    parsed = parser.parse(blob_ref, ParseOptions(parser_name=options.parser_name))
    pieces = chunk_text(
        parsed.text,
        chunk_size=options.chunk_size,
        chunk_overlap=options.chunk_overlap,
        token_limit=max(options.chunk_size // 4, 1),
    )
    vectors = embedder.embed_texts(pieces) if pieces else []

    chunks: list[Chunk] = []
    vector_items: list[VectorItem] = []

    for idx, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)):
        chunk = Chunk(
            id=str(uuid4()),
            collection_id=collection_id,
            document_id=document.id,
            text=piece,
            token_count=estimate_token_count(piece),
            order=idx,
            metadata=parsed.metadata,
        )
        chunks.append(chunk)
        vector_items.append(
            VectorItem(
                id=chunk.id,
                vector=vector,
                collection_id=collection_id,
                document_id=document.id,
                chunk_id=chunk.id,
                metadata={"order": idx, **chunk.metadata},
            )
        )

    if chunks:
        chunk_store.upsert_chunks(chunks)
        vector_index.upsert(vector_items)

    document.status = DocumentStatus.INGESTED
    document.metadata = {**document.metadata, **parsed.metadata}
    document.updated_at = datetime.now(UTC)
    return document_store.update_document(document)


def retrieve(
    *,
    query: str,
    collection_ids: list[str],
    top_k: int,
    include_chunks: bool,
    filters: MetadataFilter | None,
    embedder: Embedder,
    vector_index: VectorIndex,
    chunk_store: ChunkStore,
    document_store: DocumentStore,
) -> RetrieveResult:
    query_vector = embedder.embed_query(query)
    raw_hits = vector_index.query(query_vector, top_k=top_k, filter=filters)

    filtered_hits = [hit for hit in raw_hits if hit.collection_id in collection_ids]
    chunk_map = {chunk.id: chunk for chunk in chunk_store.get_chunks([h.chunk_id for h in filtered_hits])}

    results: list[RetrieveHit] = []
    for hit in filtered_hits:
        chunk = chunk_map.get(hit.chunk_id)
        if chunk is None:
            continue
        if not match_metadata(chunk.metadata, filters):
            continue
        doc = document_store.get_document(chunk.document_id)
        if doc is None:
            continue

        snippet = chunk.text[:280]
        citation = Citation(
            document_id=doc.id,
            chunk_id=chunk.id,
            snippet=snippet,
            page=chunk.metadata.get("page"),
            start_char=0,
            end_char=min(len(chunk.text), len(snippet)),
        )
        results.append(
            RetrieveHit(
                chunk_id=chunk.id,
                score=hit.score,
                text=chunk.text if include_chunks else None,
                citation=citation,
                document={
                    "id": doc.id,
                    "title": doc.title,
                    "collection_id": doc.collection_id,
                    "metadata": doc.metadata,
                },
            )
        )

    return RetrieveResult(query=query, hits=results)


def delete_document(
    *,
    collection_id: str,
    document_id: str,
    document_store: DocumentStore,
    chunk_store: ChunkStore,
    vector_index: VectorIndex,
) -> None:
    vector_index.delete_by_document(collection_id=collection_id, document_id=document_id)
    chunk_store.delete_chunks_by_document(document_id)
    document_store.delete_document(document_id)
