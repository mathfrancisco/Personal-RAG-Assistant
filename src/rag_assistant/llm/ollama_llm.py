"""Adaptador de LLM via Ollama (local, primário — $0, sem quota)."""

from __future__ import annotations

from collections.abc import Iterator

from rag_assistant.domain.models import LLMResponse


class OllamaLLM:
    def __init__(self, model: str, base_url: str, *, temperature: float = 0.0) -> None:
        from langchain_ollama import ChatOllama

        self.model_id = model
        self._chat = ChatOllama(model=model, base_url=base_url, temperature=temperature)

    def generate(self, prompt: str) -> LLMResponse:
        msg = self._chat.invoke(prompt)
        usage = getattr(msg, "usage_metadata", None) or {}
        return LLMResponse(
            text=str(msg.content),
            model=self.model_id,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )

    def stream(self, prompt: str) -> Iterator[str]:
        for chunk in self._chat.stream(prompt):
            text = getattr(chunk, "content", "")
            if text:
                yield str(text)
