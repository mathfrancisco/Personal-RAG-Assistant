"""Contratos (Ports). Os adaptadores concretos implementam estas interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rag_assistant.domain.models import EmbeddedChunk, RetrievedChunk


@runtime_checkable
class EmbeddingProvider(Protocol):
    model_id: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


@runtime_checkable
class VectorStore(Protocol):
    def upsert(self, chunks: list[EmbeddedChunk]) -> None: ...

    def query(self, vector: list[float], k: int) -> list[RetrievedChunk]: ...

    def delete_by_source(self, source: str) -> None: ...

    def known_sources(self) -> dict[str, str]:
        """Mapa source -> doc_hash já indexado (para reindex incremental)."""
        ...
