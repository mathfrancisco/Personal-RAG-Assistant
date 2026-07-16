"""Montagem do prompt RAG: regras de ancoragem + contexto numerado.

Regras-chave (SDD): responder só com base no contexto; se não estiver lá,
dizer que não sabe; citar as fontes usadas pelo número `[n]`.
"""

from __future__ import annotations

from rag_assistant.domain.models import RetrievedChunk

SYSTEM_RULES = (
    "Você é um assistente que responde SOMENTE com base no CONTEXTO fornecido.\n"
    "Regras:\n"
    "1. Se a resposta não estiver no contexto, diga exatamente: "
    '"Não encontrei essa informação nos documentos." Não invente.\n'
    "2. Cite as fontes usadas pelo número entre colchetes, ex.: [1], [2].\n"
    "3. Seja direto e responda no idioma da pergunta.\n"
)

NO_CONTEXT_ANSWER = "Não encontrei essa informação nos documentos."


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Blocos numerados `[n] fonte (p.X): texto` — o `n` casa com a citação."""
    blocks = []
    for i, c in enumerate(chunks, start=1):
        loc = c.source + (f", p.{c.page}" if c.page is not None else "")
        blocks.append(f"[{i}] {loc}:\n{c.text.strip()}")
    return "\n\n".join(blocks)


def build_prompt(query: str, chunks: list[RetrievedChunk]) -> str:
    context = format_context(chunks)
    return (
        f"{SYSTEM_RULES}\n"
        f"CONTEXTO:\n{context}\n\n"
        f"PERGUNTA: {query.strip()}\n\n"
        f"RESPOSTA (cite as fontes com [n]):"
    )
