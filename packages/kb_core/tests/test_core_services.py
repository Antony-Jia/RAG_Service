from kb_core.models import Citation, RetrieveHit
from kb_core.services.chunker import chunk_text
from kb_core.services.metadata_filter import match_metadata


def test_chunk_text_respects_overlap() -> None:
    text = "abcdefghijklmnopqrstuvwxyz" * 3
    chunks = chunk_text(text, chunk_size=20, chunk_overlap=5)

    assert len(chunks) >= 3
    assert chunks[0][-5:] == chunks[1][:5]


def test_match_metadata_equals() -> None:
    from kb_core.models import MetadataFilter

    metadata = {"author": "alice", "lang": "zh"}
    assert match_metadata(metadata, MetadataFilter(equals={"author": "alice"}))
    assert not match_metadata(metadata, MetadataFilter(equals={"author": "bob"}))


def test_citation_structure() -> None:
    citation = Citation(document_id="d1", chunk_id="c1", snippet="hello", page=1)
    hit = RetrieveHit(chunk_id="c1", score=0.8, citation=citation, document={"id": "d1"})
    assert hit.citation.document_id == "d1"
    assert hit.citation.page == 1
