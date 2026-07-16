"""Escolhe o adaptador de embedding conforme a config."""

from __future__ import annotations

from rag_assistant.config.settings import EmbeddingProvider, Settings
from rag_assistant.domain.ports import EmbeddingProvider as EmbeddingPort


def build_embedding_provider(settings: Settings) -> EmbeddingPort:
    if settings.embedding_provider is EmbeddingProvider.ollama:
        from rag_assistant.embeddings.ollama_embeddings import OllamaEmbeddingProvider

        return OllamaEmbeddingProvider(settings.ollama_embed_model, settings.ollama_base_url)

    if settings.embedding_provider is EmbeddingProvider.gemini:
        from rag_assistant.embeddings.gemini_embeddings import GeminiEmbeddingProvider

        return GeminiEmbeddingProvider(settings.gemini_embed_model, settings.gemini_api_key)

    raise ValueError(f"EMBEDDING_PROVIDER não suportado no V1: {settings.embedding_provider}")
