"""Adaptador de embedding via Google Gemini (free tier, opcional).

Atenção: trocar o embedder muda o espaço vetorial → exige reindexar (SDD §5.6).
"""

from __future__ import annotations


class GeminiEmbeddingProvider:
    def __init__(self, model: str, api_key: str | None) -> None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        self.model_id = model
        self._emb = GoogleGenerativeAIEmbeddings(model=f"models/{model}", google_api_key=api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._emb.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._emb.embed_query(text)
