import pytest

from rag_assistant.config.settings import EmbeddingProvider, LLMProvider, RagMode, Settings


def _make(**kw) -> Settings:
    # _env_file=None: ignora qualquer .env do disco; controlamos tudo via kwargs.
    return Settings(_env_file=None, **kw)


def test_defaults_run_fully_local_without_any_key():
    s = _make()
    assert s.rag_mode is RagMode.local
    assert s.llm_provider is LLMProvider.ollama
    assert s.embedding_provider is EmbeddingProvider.ollama
    assert s.embedding_model_id == "nomic-embed-text"
    assert s.collection_name == "chunks__nomic-embed-text"
    assert s.fallback_enabled is False  # modo local não faz fallback de nuvem


def test_hybrid_fallback_enabled_only_with_key():
    with_key = _make(rag_mode=RagMode.hybrid, gemini_api_key="k")
    assert with_key.fallback_enabled is True

    without_key = _make(rag_mode=RagMode.hybrid, gemini_api_key=None)
    # best-effort: sem key o fallback é só desativado, não é erro
    assert without_key.fallback_enabled is False


def test_cloud_primary_llm_requires_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        _make(llm_provider=LLMProvider.gemini, gemini_api_key=None)


def test_cloud_embedding_requires_key_even_in_local_mode():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        _make(embedding_provider=EmbeddingProvider.gemini, gemini_api_key=None)


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError, match="CHUNK_OVERLAP"):
        _make(chunk_size=200, chunk_overlap=200)


def test_collection_name_reflects_embed_model():
    s = _make(
        embedding_provider=EmbeddingProvider.gemini,
        gemini_api_key="k",
        gemini_embed_model="text-embedding-004",
    )
    assert s.collection_name == "chunks__text-embedding-004"


def test_ollama_model_tag_is_sanitized_in_collection():
    s = _make(ollama_embed_model="nomic-embed-text:latest")
    assert s.collection_name == "chunks__nomic-embed-text_latest"
