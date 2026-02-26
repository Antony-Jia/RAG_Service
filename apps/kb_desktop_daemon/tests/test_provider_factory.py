from kb_desktop_daemon.adapters.providers import (
    OllamaEmbedder,
    OllamaLLMClient,
    OpenCompatEmbedder,
    OpenCompatLLMClient,
    ProviderFactory,
)
from kb_desktop_daemon.config import Settings


def test_provider_factory_default_ollama() -> None:
    settings = Settings(
        app_data_dir="./data-test",
        llm_provider="ollama",
        embedding_provider="ollama",
    )
    factory = ProviderFactory(settings)
    assert isinstance(factory.create_embedder(), OllamaEmbedder)
    assert isinstance(factory.create_llm_client(), OllamaLLMClient)


def test_provider_factory_supports_mixed_providers() -> None:
    settings = Settings(
        app_data_dir="./data-test",
        llm_provider="ollama",
        embedding_provider="open_compat",
        open_compat_api_key="key",
    )
    factory = ProviderFactory(settings)
    assert isinstance(factory.create_embedder(), OpenCompatEmbedder)
    assert isinstance(factory.create_llm_client(provider="open_compat"), OpenCompatLLMClient)
