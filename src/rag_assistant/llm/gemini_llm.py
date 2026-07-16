"""Adaptador de LLM via Google Gemini (free tier — fallback de geração).

Envolto por `ratelimit` (throttle RPM + backoff em 429/ResourceExhausted),
pois o free tier tem RPD/RPM limitados.
"""

from __future__ import annotations

from collections.abc import Iterator

from rag_assistant.common.ratelimit import with_retry
from rag_assistant.domain.models import LLMResponse


class GeminiLLM:
    def __init__(
        self, model: str, api_key: str | None, *, temperature: float = 0.0
    ) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        self.model_id = model
        self._chat = ChatGoogleGenerativeAI(
            model=model, google_api_key=api_key, temperature=temperature
        )

    @with_retry
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
