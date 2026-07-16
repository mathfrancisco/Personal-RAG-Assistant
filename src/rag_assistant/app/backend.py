"""Lógica do frontend isolada do Streamlit (testável sem UI).

O `streamlit_app.py` só cuida de widgets/estado; aqui ficam a construção do
pipeline (com overrides do sidebar) e helpers puros de histórico/formatação.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rag_assistant.config.settings import LLMProvider, RagMode, Settings
from rag_assistant.domain.models import RetrievedChunk
from rag_assistant.rag.pipeline import RAGPipeline
from rag_assistant.retrieval.retriever import Retriever


def resolve_settings(mode: str, provider: str) -> Settings:
    """Aplica escolhas do sidebar sobre a config base (sem reiniciar o app)."""
    base = Settings()
    return base.model_copy(
        update={"rag_mode": RagMode(mode), "llm_provider": LLMProvider(provider)}
    )


def build_pipeline(settings: Settings) -> RAGPipeline:
    from rag_assistant.embeddings.factory import build_embedding_provider
    from rag_assistant.llm.factory import build_llm
    from rag_assistant.vectorstore.chroma_store import ChromaVectorStore

    embedder = build_embedding_provider(settings)
    store = ChromaVectorStore(
        settings.chroma_path, settings.collection_name, settings.embedding_model_id
    )
    retriever = Retriever(embedder, store, settings.top_k)
    return RAGPipeline(retriever, build_llm(settings))


def provider_badge(settings: Settings) -> str:
    """Texto do indicador de provider ativo."""
    if settings.rag_mode is RagMode.local:
        return f"🖥️ local · {settings.llm_provider.value} ({settings.ollama_llm_model})"
    fb = "Gemini" if settings.fallback_enabled else "sem fallback (falta key)"
    return f"🔀 hybrid · {settings.llm_provider.value} → fallback {fb}"


def source_label(chunk: RetrievedChunk) -> str:
    loc = chunk.source + (f", p.{chunk.page}" if chunk.page is not None else "")
    return f"{loc} · chunk #{chunk.chunk_index} · score {chunk.score:.3f}"


@dataclass
class ChatHistory:
    """Histórico da conversa — puro, sem dependência de Streamlit."""

    messages: list[dict] = field(default_factory=list)

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_assistant(self, text: str, sources: list[RetrievedChunk] | None = None) -> None:
        self.messages.append({"role": "assistant", "content": text, "sources": sources or []})

    def clear(self) -> None:
        self.messages.clear()
