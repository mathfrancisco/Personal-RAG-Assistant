"""RAGPipeline com LLM fake: cita fonte quando há contexto; sem contexto → não sabe."""

from rag_assistant.domain.models import LLMResponse, RetrievedChunk
from rag_assistant.rag.pipeline import RAGPipeline
from rag_assistant.rag.prompts import NO_CONTEXT_ANSWER


class FakeRetriever:
    def __init__(self, hits: list[RetrievedChunk]) -> None:
        self._hits = hits

    def retrieve(self, query: str, k=None):  # noqa: ARG002
        return self._hits


class EchoLLM:
    """Responde citando sempre [1], para exercitar a extração de fontes."""

    model_id = "fake-llm"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> LLMResponse:  # noqa: ARG002
        self.calls += 1
        return LLMResponse(text="Resposta ancorada [1].", model=self.model_id)

    def stream(self, prompt: str):  # noqa: ARG002
        yield "Resposta ancorada [1]."


def test_ask_with_context_returns_answer_with_source():
    hits = [RetrievedChunk("trecho relevante", "doc.txt", 0, 0.9)]
    llm = EchoLLM()
    ans = RAGPipeline(FakeRetriever(hits), llm).ask("pergunta")
    assert ans.sources and ans.sources[0].source == "doc.txt"
    assert "[1]" in ans.text
    assert llm.calls == 1


def test_ask_without_context_short_circuits_llm():
    llm = EchoLLM()
    ans = RAGPipeline(FakeRetriever([]), llm).ask("pergunta fora do corpus")
    assert ans.text == NO_CONTEXT_ANSWER
    assert ans.sources == []
    assert llm.calls == 0  # não gastou o LLM


def test_min_score_filters_weak_hits():
    hits = [RetrievedChunk("fraco", "doc.txt", 0, 0.1)]
    llm = EchoLLM()
    ans = RAGPipeline(FakeRetriever(hits), llm, min_score=0.5).ask("pergunta")
    assert ans.text == NO_CONTEXT_ANSWER
    assert llm.calls == 0
