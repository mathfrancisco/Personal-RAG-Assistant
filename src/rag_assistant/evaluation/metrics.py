"""Métricas puras: Recall@k e custo calculado (USD-equivalente do tier pago).

Custo REAL do projeto = $0 (Ollama local / Gemini free tier). A tabela de preços
serve só para reportar "quanto custaria" no tier pago — é o número que interessa
a quem for reproduzir em escala. Ollama = $0 (roda local).
"""

from __future__ import annotations

# USD por 1M tokens (input, output). Fonte: docs públicas dos providers (V1, aproximado).
PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "text-embedding-004": (0.0, 0.0),  # embedding cobrado à parte; desprezível no tier free
    "llama3.2:3b": (0.0, 0.0),  # local
    "nomic-embed-text": (0.0, 0.0),  # local
}


def source_hit(expected: str, retrieved: list[str], *, k: int) -> bool:
    """A fonte esperada aparece (por substring) entre os top-k recuperados?"""
    if not expected:
        return False
    return any(expected in src for src in retrieved[:k])


def recall_at_k(hits: list[bool]) -> float:
    """Fração de perguntas em que a fonte esperada caiu no top-k."""
    if not hits:
        return 0.0
    return sum(1 for h in hits if h) / len(hits)


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Custo calculado (USD-equivalente do tier pago) para os tokens dados."""
    price_in, price_out = PRICE_PER_MTOK.get(model, (0.0, 0.0))
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000
