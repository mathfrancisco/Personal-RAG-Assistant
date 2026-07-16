"""RAGPipeline: orquestra retrieve → prompt → generate → citar.

Curto-circuito: sem contexto relevante, responde "não encontrei" sem chamar o
LLM (economiza tokens/quota). Suporta streaming token a token. Emite um trace
por query (tempos, chunks, tokens) via um Tracer injetável.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator

from rag_assistant.domain.models import Answer, RetrievedChunk
from rag_assistant.domain.ports import LLMProvider
from rag_assistant.observability.tracer import NullTracer, Tracer
from rag_assistant.rag.citations import cited_sources
from rag_assistant.rag.prompts import NO_CONTEXT_ANSWER, build_prompt
from rag_assistant.retrieval.retriever import Retriever


class RAGPipeline:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLMProvider,
        *,
        min_score: float = 0.0,
        tracer: Tracer | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._min_score = min_score
        self._tracer = tracer or NullTracer()
        self._clock = clock

    def _relevant(self, query: str, k: int | None) -> list[RetrievedChunk]:
        hits = self._retriever.retrieve(query, k)
        return [h for h in hits if h.score >= self._min_score]

    def ask(self, query: str, k: int | None = None) -> Answer:
        t0 = self._clock()
        chunks = self._relevant(query, k)
        t1 = self._clock()

        if not chunks:
            answer = Answer(text=NO_CONTEXT_ANSWER, sources=[], model=self._llm.model_id)
            self._emit(query, chunks, answer, retrieval_ms=(t1 - t0) * 1000, generation_ms=0.0)
            return answer

        prompt = build_prompt(query, chunks)
        resp = self._llm.generate(prompt)
        t2 = self._clock()
        answer = Answer(
            text=resp.text,
            sources=cited_sources(resp.text, chunks),
            model=resp.model,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
        )
        self._emit(
            query, chunks, answer, retrieval_ms=(t1 - t0) * 1000, generation_ms=(t2 - t1) * 1000
        )
        return answer

    def ask_stream(
        self, query: str, k: int | None = None
    ) -> tuple[Iterator[str], list[RetrievedChunk]]:
        """Retorna (stream de tokens, fontes recuperadas).

        As fontes citadas só podem ser resolvidas após o texto completo, então
        aqui devolvemos os chunks recuperados; o chamador cita ao final se quiser.
        """
        chunks = self._relevant(query, k)
        if not chunks:
            return iter([NO_CONTEXT_ANSWER]), []
        prompt = build_prompt(query, chunks)
        return self._llm.stream(prompt), chunks

    def _emit(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        answer: Answer,
        *,
        retrieval_ms: float,
        generation_ms: float,
    ) -> None:
        self._tracer.trace(
            {
                "query": query,
                "model": answer.model,
                "chunks": [
                    {"source": c.source, "chunk_index": c.chunk_index, "score": c.score}
                    for c in chunks
                ],
                "answer": answer.text,
                "n_sources": len(answer.sources),
                "input_tokens": answer.input_tokens,
                "output_tokens": answer.output_tokens,
                "retrieval_ms": round(retrieval_ms, 2),
                "generation_ms": round(generation_ms, 2),
            }
        )
