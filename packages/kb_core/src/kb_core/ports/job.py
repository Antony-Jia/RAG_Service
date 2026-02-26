from datetime import datetime
from typing import Protocol

from kb_core.models import Job, JobStatus, JobType


class JobStore(Protocol):
    def create_job(self, job: Job) -> Job: ...

    def get_job(self, job_id: str) -> Job | None: ...

    def list_jobs(self, limit: int, offset: int, status: JobStatus | None = None) -> list[Job]: ...

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
        payload: dict | None = None,
        job_type: JobType | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> Job: ...
