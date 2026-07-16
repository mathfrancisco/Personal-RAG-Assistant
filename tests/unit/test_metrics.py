"""Métricas: Recall@k com casos conhecidos + cálculo de custo por tokens."""

from rag_assistant.evaluation.metrics import cost_usd, recall_at_k, source_hit


def test_source_hit_respects_topk_and_substring():
    retrieved = ["docs/contrato.pdf", "docs/politica.md", "docs/outro.txt"]
    assert source_hit("contrato", retrieved, k=5) is True
    assert source_hit("politica", retrieved, k=1) is False  # fora do top-1
    assert source_hit("inexistente", retrieved, k=5) is False
    assert source_hit("", retrieved, k=5) is False


def test_recall_at_k_fraction():
    assert recall_at_k([True, True, False, False]) == 0.5
    assert recall_at_k([True, True]) == 1.0
    assert recall_at_k([]) == 0.0


def test_cost_zero_for_local_models():
    assert cost_usd("llama3.2:3b", 1000, 1000) == 0.0
    assert cost_usd("nomic-embed-text", 5000, 0) == 0.0


def test_cost_gemini_flash_lite():
    # 1M in @ 0.10 + 1M out @ 0.40 = 0.50
    assert cost_usd("gemini-2.5-flash-lite", 1_000_000, 1_000_000) == 0.5
    assert cost_usd("gemini-2.5-flash-lite", 0, 0) == 0.0
