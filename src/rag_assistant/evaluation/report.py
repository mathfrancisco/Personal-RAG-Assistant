"""Serializa o EvalReport em Markdown (README) e JSON (aba Métricas/CI)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from rag_assistant.evaluation.models import EvalReport


def to_dict(report: EvalReport) -> dict:
    return asdict(report)


def to_markdown(report: EvalReport) -> str:
    r = report
    lines = [
        f"# Relatório de Avaliação — {r.provider or r.model}",
        "",
        f"- **Modelo (LLM):** `{r.model}`",
        f"- **Embedding:** `{r.embedding_model}`",
        f"- **Perguntas:** {r.n_queries} · **k:** {r.k}",
        "",
        "| Métrica | Valor |",
        "|---|---|",
        f"| Recall@{r.k} | **{r.recall_at_k:.2%}** |",
        f"| Tokens médios (in/out) | {r.avg_input_tokens:.0f} / {r.avg_output_tokens:.0f} |",
        f"| Custo calculado (tier pago) | US$ {r.total_cost_usd:.6f} |",
        "| Custo real | **US$ 0.00** |",
        f"| Latência retrieval (média) | {r.avg_retrieval_ms:.1f} ms |",
        f"| Latência geração (média) | {r.avg_generation_ms:.1f} ms |",
    ]
    return "\n".join(lines) + "\n"


def write_reports(report: EvalReport, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "report.md"
    json_path = out / "report.json"
    md_path.write_text(to_markdown(report), encoding="utf-8")
    json_path.write_text(
        json.dumps(to_dict(report), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return md_path, json_path
