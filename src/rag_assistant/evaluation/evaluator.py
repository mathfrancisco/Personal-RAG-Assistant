"""Roda o golden set ponta a ponta e agrega métricas (reproduzível).

Reprodutibilidade: temperature=0 + modelo pinado (responsabilidade do adapter) e
cache de respostas → reruns não gastam quota. A latência é medida por estágio
(retrieval vs geração) com um relógio injetável (testável sem sleep real).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path

from rag_assistant.domain.ports import EmbeddingProvider, LLMProvider, VectorStore
from rag_assistant.evaluation.metrics import cost_usd, recall_at_k, source_hit
from rag_assistant.evaluation.models import EvalReport, GoldenItem, QueryResult
from rag_assistant.rag.prompts import NO_CONTEXT_ANSWER, build_prompt
from rag_assistant.retrieval.retriever import Retriever


def load_golden_set(path: str | Path) -> list[GoldenItem]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        GoldenItem(
            question=item["question"],
            expected_source=item.get("expected_source", ""),
            out_of_corpus=item.get("out_of_corpus", False),
        )
        for item in data
    ]


def _answer_key(model: str, prompt: str) -> str:
    return f"ans:{model}:{hashlib.sha256(prompt.encode('utf-8')).hexdigest()}"


def evaluate(
    golden: list[GoldenItem],
    *,
    embedder: EmbeddingProvider,
    store: VectorStore,
    llm: LLMProvider,
    k: int,
    provider: str = "",
    answer_cache=None,
    clock: Callable[[], float] = time.perf_counter,
) -> EvalReport:
    retriever = Retriever(embedder, store, k)
    results: list[QueryResult] = []

    for item in golden:
        t0 = clock()
        hits = retriever.retrieve(item.question, k)
        t1 = clock()
        retrieved = [h.source for h in hits]

        # out_of_corpus: acerto = NÃO ter contexto (curto-circuito, sem chamar LLM)
        if item.out_of_corpus:
            results.append(
                QueryResult(
                    question=item.question,
                    expected_source=item.expected_source,
                    retrieved_sources=retrieved,
                    hit=not hits,  # ideal: nada recuperado → responde "não sei"
                    answered=bool(hits),
                    input_tokens=0,
                    output_tokens=0,
                    retrieval_ms=(t1 - t0) * 1000,
                    generation_ms=0.0,
                )
            )
            continue

        hit = source_hit(item.expected_source, retrieved, k=k)

        if not hits:
            results.append(
                QueryResult(
                    question=item.question,
                    expected_source=item.expected_source,
                    retrieved_sources=retrieved,
                    hit=hit,
                    answered=False,
                    input_tokens=0,
                    output_tokens=0,
                    retrieval_ms=(t1 - t0) * 1000,
                    generation_ms=0.0,
                )
            )
            continue

        prompt = build_prompt(item.question, hits)
        key = _answer_key(llm.model_id, prompt)
        cached = answer_cache.get(key) if answer_cache is not None else None

        t2 = clock()
        if cached is not None:
            text, in_tok, out_tok = cached["text"], cached["in"], cached["out"]
        else:
            resp = llm.generate(prompt)
            text, in_tok, out_tok = resp.text, resp.input_tokens, resp.output_tokens
            if answer_cache is not None:
                answer_cache.put(key, {"text": text, "in": in_tok, "out": out_tok})
        t3 = clock()

        results.append(
            QueryResult(
                question=item.question,
                expected_source=item.expected_source,
                retrieved_sources=retrieved,
                hit=hit,
                answered=text.strip() != NO_CONTEXT_ANSWER,
                input_tokens=in_tok,
                output_tokens=out_tok,
                retrieval_ms=(t1 - t0) * 1000,
                generation_ms=(t3 - t2) * 1000,
            )
        )

    return _aggregate(results, llm=llm, embedder=embedder, k=k, provider=provider)


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _aggregate(
    results: list[QueryResult],
    *,
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    k: int,
    provider: str,
) -> EvalReport:
    total_cost = sum(cost_usd(llm.model_id, r.input_tokens, r.output_tokens) for r in results)
    return EvalReport(
        provider=provider,
        model=llm.model_id,
        embedding_model=getattr(embedder, "model_id", ""),
        k=k,
        n_queries=len(results),
        recall_at_k=recall_at_k([r.hit for r in results]),
        avg_input_tokens=_avg([r.input_tokens for r in results]),
        avg_output_tokens=_avg([r.output_tokens for r in results]),
        total_cost_usd=total_cost,
        avg_retrieval_ms=_avg([r.retrieval_ms for r in results]),
        avg_generation_ms=_avg([r.generation_ms for r in results]),
        results=results,
    )
