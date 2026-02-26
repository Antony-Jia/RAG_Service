from typing import Protocol

from kb_core.models import MetadataFilter, VectorHit, VectorItem


class VectorIndex(Protocol):
    def upsert(self, items: list[VectorItem]) -> None: ...

    def query(
        self,
        vector: list[float],
        top_k: int,
        filter: MetadataFilter | None = None,
    ) -> list[VectorHit]: ...

    def delete_by_document(self, collection_id: str, document_id: str) -> None: ...
