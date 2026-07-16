"""Extrai os números `[n]` citados na resposta e mapeia para os chunks usados.

Se o modelo não citar nenhuma fonte (desobedeceu a regra), devolve-se a lista
completa de chunks recuperados como fallback — melhor rastreável que vazio.
"""

from __future__ import annotations

import re

from rag_assistant.domain.models import RetrievedChunk

_CITE = re.compile(r"\[(\d+)\]")


def cited_sources(answer: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    nums = {int(m) for m in _CITE.findall(answer)}
    picked = [chunks[n - 1] for n in sorted(nums) if 1 <= n <= len(chunks)]
    return picked or list(chunks)
