"""Traces de cada query RAG — Langfuse (se houver keys) ou JSON local (fallback).

Cada trace guarda: query, chunks recuperados (fonte/score), prompt final, resposta,
tempos (retrieval/geração) e tokens. Sem keys de Langfuse, grava um JSONL em
`data/traces/` — nenhuma dependência de nuvem exigida (modo local continua $0/offline).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class Tracer(Protocol):
    def trace(self, record: dict[str, Any]) -> None: ...


class NullTracer:
    """Descarta tudo — usado quando observabilidade está desligada/em teste."""

    def trace(self, record: dict[str, Any]) -> None:  # noqa: D102
        return None


class JsonTracer:
    """Anexa cada trace como uma linha JSON em `<dir>/traces.jsonl`."""

    def __init__(self, out_dir: str | Path) -> None:
        self._dir = Path(out_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "traces.jsonl"

    def trace(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    @property
    def path(self) -> Path:
        return self._path


class LangfuseTracer:
    """Envia o trace para o Langfuse (import preguiçoso — dep opcional)."""

    def __init__(self, public_key: str, secret_key: str) -> None:
        from langfuse import Langfuse

        self._client = Langfuse(public_key=public_key, secret_key=secret_key)

    def trace(self, record: dict[str, Any]) -> None:
        self._client.trace(name="rag_query", input=record.get("query"), output=record)


def build_tracer(settings) -> Tracer:
    """Langfuse se ambas as keys existirem; senão JSON local (fallback)."""
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            return LangfuseTracer(settings.langfuse_public_key, settings.langfuse_secret_key)
        except Exception:  # noqa: BLE001 - Langfuse indisponível → cai para JSON local
            pass
    return JsonTracer(getattr(settings, "traces_path", "./data/traces"))
