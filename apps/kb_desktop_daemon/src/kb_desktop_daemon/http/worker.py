from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from datetime import UTC, datetime

from kb_core.models import JobStatus


def utcnow() -> datetime:
    return datetime.now(UTC)


class JobWorker:
    def __init__(self, repo: object) -> None:
        self._repo = repo
        self._queue: queue.Queue[tuple[str, Callable[[], None]]] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=2)

    def submit(self, job_id: str, fn: Callable[[], None]) -> None:
        self._queue.put((job_id, fn))

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                job_id, fn = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            self._repo.update_job(job_id, status=JobStatus.RUNNING, progress=10, started_at=utcnow())
            try:
                fn()
                self._repo.update_job(
                    job_id,
                    status=JobStatus.SUCCEEDED,
                    progress=100,
                    finished_at=utcnow(),
                )
            except Exception as exc:  # noqa: BLE001
                self._repo.update_job(
                    job_id,
                    status=JobStatus.FAILED,
                    message=str(exc),
                    finished_at=utcnow(),
                )
            finally:
                self._queue.task_done()
