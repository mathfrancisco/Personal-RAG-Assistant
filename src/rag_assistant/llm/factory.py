"""Escolhe o LLM conforme a config e, em modo hybrid, adiciona fallback.

Primário = Ollama (local). Em `rag_mode=hybrid` com key do fallback presente,
falha do primário (Ollama fora do ar) cai para o Gemini — best-effort.
"""

from __future__ import annotations

from collections.abc import Iterator

from rag_assistant.config.settings import LLMProvider, RagMode, Settings
from rag_assistant.domain.models import LLMResponse
from rag_assistant.domain.ports import LLMProvider as LLMPort

_CLOUD_LLM = {LLMProvider.gemini, LLMProvider.openai, LLMProvider.anthropic}


def _build(provider: LLMProvider, s: Settings) -> LLMPort:
    if provider is LLMProvider.ollama:
        from rag_assistant.llm.ollama_llm import OllamaLLM

        return OllamaLLM(s.ollama_llm_model, s.ollama_base_url)
    if provider is LLMProvider.gemini:
        from rag_assistant.llm.gemini_llm import GeminiLLM

        return GeminiLLM(s.gemini_llm_model, s.gemini_api_key)
    raise ValueError(f"LLM_PROVIDER não suportado no V1: {provider}")


class FallbackLLM:
    """Tenta o primário; em qualquer falha, usa o secundário (log e segue)."""

    def __init__(self, primary: LLMPort, secondary: LLMPort) -> None:
        self._primary = primary
        self._secondary = secondary
        self.model_id = primary.model_id

    def generate(self, prompt: str) -> LLMResponse:
        try:
            return self._primary.generate(prompt)
        except Exception:  # noqa: BLE001 - fallback é best-effort por design
            return self._secondary.generate(prompt)

    def stream(self, prompt: str) -> Iterator[str]:
        try:
            yield from self._primary.stream(prompt)
        except Exception:  # noqa: BLE001
            yield from self._secondary.stream(prompt)


def build_llm(settings: Settings) -> LLMPort:
    if settings.rag_mode is RagMode.local and settings.llm_provider in _CLOUD_LLM:
        raise ValueError(
            f"modo local proíbe LLM de nuvem ({settings.llm_provider.value}); "
            "use LLM_PROVIDER=ollama ou RAG_MODE=hybrid."
        )
    primary = _build(settings.llm_provider, settings)
    if settings.fallback_enabled and settings.llm_fallback_provider != settings.llm_provider:
        secondary = _build(settings.llm_fallback_provider, settings)
        return FallbackLLM(primary, secondary)
    return primary
