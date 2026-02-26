from kb_core.models import MetadataFilter, VectorHit, VectorItem


class PgVectorIndex:
    """TODO: implement pgvector adapter compatible with kb_core.ports.VectorIndex."""

    def upsert(self, items: list[VectorItem]) -> None:
        raise NotImplementedError

    def query(
        self,
        vector: list[float],
        top_k: int,
        filter: MetadataFilter | None = None,
    ) -> list[VectorHit]:
        raise NotImplementedError

    def delete_by_document(self, collection_id: str, document_id: str) -> None:
        raise NotImplementedError
