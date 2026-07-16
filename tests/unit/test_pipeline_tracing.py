"""RAGPipeline emite um trace por query (com/sem contexto), tempos e tokens."""

from rag_assistant.domain.models import LLMResponse, RetrievedChunk
from rag_assistant.rag.pipeline import RAGPipeline


class FakeRetriever:
    def __init__(self, hits):
        self._hits = hits

    def retrieve(self, query, k=None):  # noqa: ARG002
        return self._hits


class FakeLLM:
    model_id = "fake"

    def generate(self, prompt):  # noqa: ARG002
        return LLMResponse(text="resp [1]", model=self.model_id, input_tokens=50, output_tokens=8)

    def stream(self, prompt):  # noqa: ARG002
        yield "resp [1]"


class RecordingTracer:
    def __init__(self):
        self.records = []

    def trace(self, record):
        self.records.append(record)


def test_trace_emitted_with_context():
    tracer = RecordingTracer()
    hits = [RetrievedChunk("t", "doc.txt", 0, 0.9)]
    RAGPipeline(FakeRetriever(hits), FakeLLM(), tracer=tracer).ask("q")
    assert len(tracer.records) == 1
    rec = tracer.records[0]
    assert rec["query"] == "q"
    assert rec["output_tokens"] == 8
    assert rec["n_sources"] == 1
    assert "retrieval_ms" in rec and "generation_ms" in rec


def test_trace_emitted_without_context_no_generation():
    tracer = RecordingTracer()
    RAGPipeline(FakeRetriever([]), FakeLLM(), tracer=tracer).ask("q")
    rec = tracer.records[0]
    assert rec["generation_ms"] == 0.0
    assert rec["n_sources"] == 0
