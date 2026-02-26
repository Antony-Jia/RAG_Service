from typing import Protocol

from kb_core.models import BlobRef, ParsedDocument, ParseOptions


class Parser(Protocol):
    def can_parse(self, mime: str, ext: str) -> bool: ...

    def parse(self, blob: BlobRef, opts: ParseOptions) -> ParsedDocument: ...
