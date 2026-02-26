from typing import Protocol

from kb_core.models import BlobRef


class BlobStore(Protocol):
    def put(self, data: bytes, *, name: str, mime: str) -> BlobRef: ...

    def get(self, ref: BlobRef) -> bytes: ...
