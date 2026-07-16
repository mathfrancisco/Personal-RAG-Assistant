"""Configuração central — lê e valida `.env` (pydantic-settings).

Estratégia de provider (V1):
- **Primário:** Ollama (local, via Docker) — LLM e embeddings, $0, sem quota.
- **Fallback (só geração):** Gemini free tier, quando o Ollama está indisponível.
  O embedding NÃO tem fallback: o modelo de embedding é a identidade do índice
  (SDD §5.6), então trocá-lo exigiria reindexar. Mantém-se fixo.

Modos (`RAG_MODE`):
- `local`  → só Ollama; nenhuma chamada externa (privacidade). Fallback desligado.
- `hybrid` → Ollama primário + Gemini como fallback de geração (se houver key).

Com o default (`local` + Ollama), o projeto roda sem NENHUMA API key.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RagMode(StrEnum):
    local = "local"  # só Ollama, offline
    hybrid = "hybrid"  # Ollama primário + Gemini fallback


class LLMProvider(StrEnum):
    ollama = "ollama"
    gemini = "gemini"
    openai = "openai"  # opcional (pago)
    anthropic = "anthropic"  # opcional (pago)


class EmbeddingProvider(StrEnum):
    ollama = "ollama"
    gemini = "gemini"  # opcional (free tier, mas com quota)
    openai = "openai"  # opcional (pago)


# Chave exigida por provider quando ele é usado como PRIMÁRIO de nuvem.
_CLOUD_KEY = {
    LLMProvider.gemini: ("gemini_api_key", "GEMINI_API_KEY"),
    LLMProvider.openai: ("openai_api_key", "OPENAI_API_KEY"),
    LLMProvider.anthropic: ("anthropic_api_key", "ANTHROPIC_API_KEY"),
}
_EMBED_CLOUD_KEY = {
    EmbeddingProvider.gemini: ("gemini_api_key", "GEMINI_API_KEY"),
    EmbeddingProvider.openai: ("openai_api_key", "OPENAI_API_KEY"),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    rag_mode: RagMode = RagMode.local
    llm_provider: LLMProvider = LLMProvider.ollama
    embedding_provider: EmbeddingProvider = EmbeddingProvider.ollama

    # Fallback de geração (só usado em rag_mode=hybrid, best-effort).
    llm_fallback_provider: LLMProvider = LLMProvider.gemini

    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    gemini_llm_model: str = "gemini-2.5-flash-lite"
    gemini_embed_model: str = "text-embedding-004"
    ollama_llm_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"

    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=120, ge=0)
    top_k: int = Field(default=5, gt=0)

    chroma_path: str = "./data/chroma"
    cache_path: str = "./data/cache"
    answer_cache_path: str = "./data/answer_cache"

    golden_set_path: str = "evaluation/golden_set.json"
    eval_report_dir: str = "evaluation/reports"

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> Settings:
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP deve ser menor que CHUNK_SIZE")

        # Se o LLM PRIMÁRIO for de nuvem, a chave é obrigatória.
        if self.llm_provider in _CLOUD_KEY:
            attr, env = _CLOUD_KEY[self.llm_provider]
            if not getattr(self, attr):
                raise ValueError(f"{env} é obrigatório para LLM_PROVIDER={self.llm_provider.value}")

        # Se o embedding for de nuvem, a chave é obrigatória (qualquer modo).
        if self.embedding_provider in _EMBED_CLOUD_KEY:
            attr, env = _EMBED_CLOUD_KEY[self.embedding_provider]
            if not getattr(self, attr):
                raise ValueError(
                    f"{env} é obrigatório para EMBEDDING_PROVIDER={self.embedding_provider.value}"
                )
        # Fallback é best-effort: sem key, ele é apenas desativado (sem erro).
        return self

    @property
    def fallback_enabled(self) -> bool:
        """Fallback de geração só existe em modo hybrid e se a key do fallback estiver presente."""
        if self.rag_mode is not RagMode.hybrid:
            return False
        if self.llm_fallback_provider in _CLOUD_KEY:
            attr, _ = _CLOUD_KEY[self.llm_fallback_provider]
            return bool(getattr(self, attr))
        return True  # fallback local (raro), sempre disponível

    @property
    def embedding_model_id(self) -> str:
        """Modelo de embedding ativo — parte da identidade da coleção (SDD §5.6)."""
        return {
            EmbeddingProvider.ollama: self.ollama_embed_model,
            EmbeddingProvider.gemini: self.gemini_embed_model,
            EmbeddingProvider.openai: "text-embedding-3-small",
        }[self.embedding_provider]

    @property
    def collection_name(self) -> str:
        """Coleção Chroma por modelo de embedding — trocar o embedder muda a coleção."""
        safe = self.embedding_model_id.replace("/", "_").replace(":", "_")
        return f"chunks__{safe}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
