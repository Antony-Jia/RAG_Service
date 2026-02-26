from __future__ import annotations

from dataclasses import dataclass

import requests
from kb_core.ports import Embedder, LLMClient

from kb_desktop_daemon.config import Settings


class OllamaEmbedder(Embedder):
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dim_cache: int | None = None

    @property
    def dim(self) -> int:
        if self._dim_cache is None:
            self._dim_cache = len(self.embed_query("dimension probe"))
        return self._dim_cache

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        response = requests.post(
            f"{self._base_url}/api/embeddings",
            json={"model": self._model, "prompt": text},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["embedding"]


class OpenCompatEmbedder(Embedder):
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._dim_cache: int | None = None

    @property
    def dim(self) -> int:
        if self._dim_cache is None:
            self._dim_cache = len(self.embed_query("dimension probe"))
        return self._dim_cache

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = requests.post(
            f"{self._base_url}/embeddings",
            headers=self._headers(),
            json={"model": self._model, "input": texts},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()["data"]
        data.sort(key=lambda item: item["index"])
        return [item["embedding"] for item in data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


class OllamaLLMClient(LLMClient):
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def chat(self, messages: list[dict], *, temperature: float = 0.0) -> str:
        response = requests.post(
            f"{self._base_url}/api/chat",
            json={"model": self._model, "messages": messages, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("message", {}).get("content", "")


class OpenCompatLLMClient(LLMClient):
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def chat(self, messages: list[dict], *, temperature: float = 0.0) -> str:
        response = requests.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers(),
            json={"model": self._model, "messages": messages, "temperature": temperature},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]


@dataclass
class ProviderFactory:
    settings: Settings

    def create_embedder(self, provider: str | None = None) -> Embedder:
        selected = (provider or self.settings.embedding_provider).lower()
        if selected == "ollama":
            return OllamaEmbedder(
                base_url=self.settings.ollama_base_url,
                model=self.settings.ollama_embed_model,
            )
        if selected == "open_compat":
            return OpenCompatEmbedder(
                base_url=self.settings.open_compat_base_url,
                api_key=self.settings.open_compat_api_key,
                model=self.settings.open_compat_embed_model,
            )
        raise ValueError(f"Unsupported embedding provider: {selected}")

    def create_llm_client(self, provider: str | None = None) -> LLMClient:
        selected = (provider or self.settings.llm_provider).lower()
        if selected == "ollama":
            return OllamaLLMClient(
                base_url=self.settings.ollama_base_url,
                model=self.settings.ollama_llm_model,
            )
        if selected == "open_compat":
            return OpenCompatLLMClient(
                base_url=self.settings.open_compat_base_url,
                api_key=self.settings.open_compat_api_key,
                model=self.settings.open_compat_llm_model,
            )
        raise ValueError(f"Unsupported llm provider: {selected}")
