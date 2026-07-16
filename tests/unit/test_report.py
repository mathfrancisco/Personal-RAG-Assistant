"""Serialização do relatório: markdown legível + json redondo."""

import json

from rag_assistant.evaluation.models import EvalReport
from rag_assistant.evaluation.report import to_markdown, write_reports


def _report() -> EvalReport:
    return EvalReport(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        embedding_model="nomic-embed-text",
        k=5,
        n_queries=10,
        recall_at_k=0.9,
        avg_input_tokens=120.0,
        avg_output_tokens=42.0,
        total_cost_usd=0.000123,
        avg_retrieval_ms=12.5,
        avg_generation_ms=340.0,
    )


def test_markdown_has_recall_and_zero_real_cost():
    md = to_markdown(_report())
    assert "Recall@5 | **90.00%**" in md
    assert "US$ 0.00" in md


def test_write_reports_creates_md_and_json(tmp_path):
    md_path, json_path = write_reports(_report(), tmp_path / "reports")
    assert md_path.exists() and json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["recall_at_k"] == 0.9
    assert data["model"] == "gemini-2.5-flash-lite"
