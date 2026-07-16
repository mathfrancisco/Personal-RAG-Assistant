"""Busca semântica: pergunta → embedding → top-k chunks do vector store.

A compatibilidade embedder ↔ coleção é garantida no boot do ChromaVectorStore
(EmbeddingMismatchError, SDD §5.6), então o retriever só orquestra.
"""

from __future__ import annotations

from rag_assistant.domain.models import RetrievedChunk
from rag_assistant.domain.ports import EmbeddingProvider, VectorStore


class Retriever:
    def __init__(self, embedder: EmbeddingProvider, store: VectorStore, top_k: int) -> None:
        self._embedder = embedder
        self._store = store
        self._top_k = top_k

    def retrieve(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        text = query.strip()
        if not text:
            return []
        vector = self._embedder.embed_query(text)
        hits = self._store.query(vector, k or self._top_k)
        return sorted(hits, key=lambda c: c.score, reverse=True)
