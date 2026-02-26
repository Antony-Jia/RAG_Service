from __future__ import annotations


def estimate_token_count(text: str) -> int:
    return len(text.split())


def chunk_text(text: str, *, chunk_size: int, chunk_overlap: int, token_limit: int | None = None) -> list[str]:
    content = text.strip()
    if not content:
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(content)
    step = max(chunk_size - chunk_overlap, 1)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        candidate = content[start:end].strip()

        if token_limit is not None and estimate_token_count(candidate) > token_limit:
            words = candidate.split()
            candidate = " ".join(words[:token_limit])

        if candidate:
            chunks.append(candidate)
        if end >= text_len:
            break
        start += step

    return chunks
