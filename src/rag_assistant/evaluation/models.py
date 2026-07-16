"""Tipos da avaliação — sem I/O."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class GoldenItem:
    """Uma pergunta do golden set + a fonte onde a resposta deveria estar.

    `expected_source` casa por substring com o `source` do chunk recuperado
    (permite apontar só o nome do arquivo). `out_of_corpus=True` marca perguntas
    que DEVEM resultar em "não encontrei" (controle de alucinação).
    """

    question: str
    expected_source: str = ""
    out_of_corpus: bool = False


@dataclass(frozen=True, slots=True)
class QueryResult:
    question: str
    expected_source: str
    retrieved_sources: list[str]
    hit: bool  # fonte esperada no top-k
    answered: bool  # LLM produziu resposta (não foi "não encontrei")
    input_tokens: int
    output_tokens: int
    retrieval_ms: float
    generation_ms: float


@dataclass(slots=True)
class EvalReport:
    provider: str
    model: str
    embedding_model: str
    k: int
    n_queries: int
    recall_at_k: float
    avg_input_tokens: float
    avg_output_tokens: float
    total_cost_usd: float
    avg_retrieval_ms: float
    avg_generation_ms: float
    results: list[QueryResult] = field(default_factory=list)
