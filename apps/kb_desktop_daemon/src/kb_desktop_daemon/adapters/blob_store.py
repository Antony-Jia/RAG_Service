from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from kb_core.models import BlobRef


class LocalBlobStore:
    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes, *, name: str, mime: str) -> BlobRef:
        blob_id = str(uuid4())
        filename = f"{blob_id}_{name}"
        path = self._base_dir / filename
        path.write_bytes(data)
        return BlobRef(id=blob_id, path=str(path), name=name, mime=mime)

    def get(self, ref: BlobRef) -> bytes:
        return Path(ref.path).read_bytes()
