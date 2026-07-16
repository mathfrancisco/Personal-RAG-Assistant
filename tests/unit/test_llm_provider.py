"""Contrato do LLMProvider + comportamento do fallback (sem tocar rede/quota)."""

from rag_assistant.domain.models import LLMResponse
from rag_assistant.domain.ports import LLMProvider
from rag_assistant.llm.factory import FallbackLLM


class GoodLLM:
    model_id = "good"

    def generate(self, prompt: str) -> LLMResponse:  # noqa: ARG002
        return LLMResponse(text="ok", model=self.model_id)

    def stream(self, prompt: str):  # noqa: ARG002
        yield "ok"


class BrokenLLM:
    model_id = "broken"

    def generate(self, prompt: str) -> LLMResponse:  # noqa: ARG002
        raise ConnectionError("ollama offline")

    def stream(self, prompt: str):  # noqa: ARG002
        raise ConnectionError("ollama offline")
        yield  # pragma: no cover


def test_adapters_satisfy_protocol():
    assert isinstance(GoodLLM(), LLMProvider)
    assert isinstance(FallbackLLM(GoodLLM(), GoodLLM()), LLMProvider)


def test_fallback_uses_secondary_when_primary_fails():
    llm = FallbackLLM(BrokenLLM(), GoodLLM())
    assert llm.generate("q").text == "ok"
    assert "".join(llm.stream("q")) == "ok"


def test_fallback_prefers_primary_when_healthy():
    llm = FallbackLLM(GoodLLM(), BrokenLLM())
    assert llm.generate("q").model == "good"
