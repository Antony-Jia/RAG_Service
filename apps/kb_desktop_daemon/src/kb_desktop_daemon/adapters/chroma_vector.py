from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import chromadb
from kb_core.models import MetadataFilter, VectorHit, VectorItem

if TYPE_CHECKING:
    from kb_desktop_daemon.adapters.sqlite_store import SQLiteRepository


class ChromaVectorIndex:
    def __init__(self, persist_dir: str, repo: SQLiteRepository | None = None) -> None:
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._repo = repo

    @staticmethod
    def _collection_name(collection_id: str) -> str:
        return f"kb_{collection_id}"

    @staticmethod
    def _to_collection_id(name: str) -> str:
        return name[3:] if name.startswith("kb_") else name

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                clean[key] = value
            else:
                clean[key] = json.dumps(value, ensure_ascii=True)
        return clean

    def upsert(self, items: list[VectorItem]) -> None:
        grouped: dict[str, list[VectorItem]] = {}
        for item in items:
            grouped.setdefault(item.collection_id, []).append(item)

        for collection_id, group_items in grouped.items():
            coll = self._client.get_or_create_collection(name=self._collection_name(collection_id))
            ids = [item.id for item in group_items]
            vectors = [item.vector for item in group_items]
            metadatas = [
                self._sanitize_metadata(
                    {
                        "collection_id": item.collection_id,
                        "document_id": item.document_id,
                        "chunk_id": item.chunk_id,
                        **item.metadata,
                    }
                )
                for item in group_items
            ]
            documents = [item.chunk_id for item in group_items]
            coll.upsert(ids=ids, embeddings=vectors, metadatas=metadatas, documents=documents)

            if self._repo is not None:
                for item in group_items:
                    self._repo.upsert_chunk_vector_map(
                        chunk_id=item.chunk_id,
                        collection_id=item.collection_id,
                        document_id=item.document_id,
                        vector_id=item.id,
                    )

    def query(
        self,
        vector: list[float],
        top_k: int,
        filter: MetadataFilter | None = None,
    ) -> list[VectorHit]:
        where = filter.equals if filter and filter.equals else None
        hits: list[VectorHit] = []

        for collection in self._list_collections():
            result = collection.query(
                query_embeddings=[vector],
                n_results=top_k,
                where=where,
            )
            ids = result.get("ids", [[]])[0]
            distances = result.get("distances", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]

            for chunk_id, distance, metadata in zip(ids, distances, metadatas, strict=False):
                metadata = metadata or {}
                score = 1.0 - float(distance)
                collection_id = str(metadata.get("collection_id") or self._to_collection_id(collection.name))
                document_id = str(metadata.get("document_id") or "")
                resolved_chunk_id = str(metadata.get("chunk_id") or chunk_id)
                hits.append(
                    VectorHit(
                        id=str(chunk_id),
                        score=score,
                        collection_id=collection_id,
                        document_id=document_id,
                        chunk_id=resolved_chunk_id,
                        metadata=metadata,
                    )
                )

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:top_k]

    def delete_by_document(self, collection_id: str, document_id: str) -> None:
        coll = self._client.get_or_create_collection(name=self._collection_name(collection_id))
        coll.delete(where={"document_id": document_id})
        if self._repo is not None:
            self._repo.delete_chunk_vector_map_by_document(document_id=document_id)

    def _list_collections(self) -> list[Any]:
        collections = self._client.list_collections()
        resolved = []
        for entry in collections:
            name = entry.name if hasattr(entry, "name") else str(entry)
            if name.startswith("kb_"):
                resolved.append(self._client.get_collection(name=name))
        return resolved
