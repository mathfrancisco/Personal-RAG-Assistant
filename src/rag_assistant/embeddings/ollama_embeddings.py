"""Adaptador de embedding via Ollama (local, primário)."""

from __future__ import annotations


class OllamaEmbeddingProvider:
    def __init__(self, model: str, base_url: str) -> None:
        from langchain_ollama import OllamaEmbeddings

        self.model_id = model
        self._emb = OllamaEmbeddings(model=model, base_url=base_url)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._emb.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._emb.embed_query(text)
