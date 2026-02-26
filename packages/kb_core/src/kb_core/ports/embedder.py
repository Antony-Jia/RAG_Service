from typing import Protocol


class Embedder(Protocol):
    @property
    def dim(self) -> int: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class LLMClient(Protocol):
    def chat(self, messages: list[dict], *, temperature: float = 0.0) -> str: ...
