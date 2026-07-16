"""Evaluator: métricas agregadas + determinismo (rerun com cache = 0 chamadas)."""

from rag_assistant.domain.models import LLMResponse, RetrievedChunk
from rag_assistant.evaluation.evaluator import evaluate
from rag_assistant.evaluation.models import GoldenItem


class CountingLLM:
    model_id = "gemini-2.5-flash-lite"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str) -> LLMResponse:  # noqa: ARG002
        self.calls += 1
        return LLMResponse(text="Resposta [1].", model=self.model_id,
                           input_tokens=100, output_tokens=20)

    def stream(self, prompt):  # noqa: ARG002
        yield "Resposta [1]."


class DictCache:
    def __init__(self):
        self._d = {}

    def get(self, key):
        return self._d.get(key)

    def put(self, key, value):
        self._d[key] = value


class RoutingStore:
    """Store que devolve hits conforme a pergunta em curso (setada pelo retriever fake)."""

    def __init__(self):
        self.pending = []

    def set_hits(self, hits):
        self.pending = hits

    def query(self, vector, k):  # noqa: ARG002
        return self.pending


class RoutingEmbedder:
    """Embedder que, ao embedar a query, informa o store quais hits devolver."""

    model_id = "fake-embed"

    def __init__(self, store: RoutingStore):
        self._store = store

    def embed_query(self, text: str):
        self._store.set_hits(
            [RetrievedChunk("prazo 30 dias", "docs/contrato.pdf", 0, 0.9)]
            if "contrato" in text.lower()
            else []
        )
        return [1.0, 0.0]

    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]


def _golden():
    return [
        GoldenItem("Qual o prazo do contrato?", "contrato"),
        GoldenItem("Receita de bolo?", "", out_of_corpus=True),
    ]


def test_evaluate_computes_recall_and_tokens():
    store = RoutingStore()
    embedder = RoutingEmbedder(store)
    llm = CountingLLM()

    rep = evaluate(_golden(), embedder=embedder, store=store, llm=llm, k=5, provider="gemini")

    assert rep.n_queries == 2
    # 1 pergunta de corpus acerta a fonte; a out-of-corpus acerta por não recuperar nada
    assert rep.recall_at_k == 1.0
    assert rep.avg_output_tokens == 10  # (20 + 0) / 2
    assert rep.total_cost_usd > 0
    assert llm.calls == 1  # out-of-corpus não chama o LLM


def test_rerun_with_cache_makes_zero_new_calls():
    store = RoutingStore()
    embedder = RoutingEmbedder(store)
    llm = CountingLLM()
    cache = DictCache()

    r1 = evaluate(_golden(), embedder=embedder, store=store, llm=llm, k=5, answer_cache=cache)
    assert llm.calls == 1
    r2 = evaluate(_golden(), embedder=embedder, store=store, llm=llm, k=5, answer_cache=cache)
    assert llm.calls == 1  # segundo run: tudo do cache, zero chamadas novas
    assert r1.recall_at_k == r2.recall_at_k
    assert r1.avg_output_tokens == r2.avg_output_tokens
