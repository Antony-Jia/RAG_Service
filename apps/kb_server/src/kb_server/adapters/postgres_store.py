from kb_core.models import Chunk, Collection, Document, Job, JobStatus, JobType


class PostgresStore:
    """TODO: implement Postgres-backed stores for documents/chunks/collections/jobs with multi-tenancy."""

    def create_document(self, doc: Document) -> Document:
        raise NotImplementedError

    def get_document(self, document_id: str) -> Document | None:
        raise NotImplementedError

    def list_documents(self, collection_id: str, limit: int, offset: int) -> list[Document]:
        raise NotImplementedError

    def update_document(self, doc: Document) -> Document:
        raise NotImplementedError

    def delete_document(self, document_id: str) -> None:
        raise NotImplementedError

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        raise NotImplementedError

    def get_chunks(self, chunk_ids: list[str]) -> list[Chunk]:
        raise NotImplementedError

    def list_chunks_by_document(self, document_id: str, limit: int, offset: int) -> list[Chunk]:
        raise NotImplementedError

    def delete_chunks_by_document(self, document_id: str) -> None:
        raise NotImplementedError

    def create_collection(self, collection: Collection) -> Collection:
        raise NotImplementedError

    def get_collection(self, collection_id: str) -> Collection | None:
        raise NotImplementedError

    def list_collections(self, limit: int, offset: int) -> list[Collection]:
        raise NotImplementedError

    def delete_collection(self, collection_id: str) -> None:
        raise NotImplementedError

    def create_job(self, job: Job) -> Job:
        raise NotImplementedError

    def get_job(self, job_id: str) -> Job | None:
        raise NotImplementedError

    def list_jobs(self, limit: int, offset: int, status: JobStatus | None = None) -> list[Job]:
        raise NotImplementedError

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
        payload: dict | None = None,
        job_type: JobType | None = None,
    ) -> Job:
        raise NotImplementedError
