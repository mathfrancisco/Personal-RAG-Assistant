"""RAGPipeline: orquestra retrieve → prompt → generate → citar.

Curto-circuito: sem contexto relevante, responde "não encontrei" sem chamar o
LLM (economiza tokens/quota). Suporta streaming token a token.
"""

from __future__ import annotations

from collections.abc import Iterator

from rag_assistant.domain.models import Answer, RetrievedChunk
from rag_assistant.domain.ports import LLMProvider
from rag_assistant.rag.citations import cited_sources
from rag_assistant.rag.prompts import NO_CONTEXT_ANSWER, build_prompt
from rag_assistant.retrieval.retriever import Retriever


class RAGPipeline:
    def __init__(
        self, retriever: Retriever, llm: LLMProvider, *, min_score: float = 0.0
    ) -> None:
        self._retriever = retriever
        self._llm = llm
        self._min_score = min_score

    def _relevant(self, query: str, k: int | None) -> list[RetrievedChunk]:
        hits = self._retriever.retrieve(query, k)
        return [h for h in hits if h.score >= self._min_score]

    def ask(self, query: str, k: int | None = None) -> Answer:
        chunks = self._relevant(query, k)
        if not chunks:
            return Answer(text=NO_CONTEXT_ANSWER, sources=[], model=self._llm.model_id)

        prompt = build_prompt(query, chunks)
        resp = self._llm.generate(prompt)
        return Answer(
            text=resp.text,
            sources=cited_sources(resp.text, chunks),
            model=resp.model,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
        )

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
