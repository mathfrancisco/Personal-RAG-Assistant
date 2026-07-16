"""CLI do Personal RAG Assistant. Os comandos ganham corpo nas fases seguintes."""

from __future__ import annotations

import typer

from rag_assistant.config.settings import get_settings

app = typer.Typer(
    add_completion=False,
    help="Personal RAG Assistant — RAG local com citação de fontes, custo $0.",
)


@app.command()
def config() -> None:
    """Mostra a configuração efetiva (sem revelar segredos)."""
    s = get_settings()
    typer.echo(f"RAG_MODE           = {s.rag_mode.value}")
    typer.echo(f"LLM_PROVIDER       = {s.llm_provider.value}")
    typer.echo(f"EMBEDDING_PROVIDER = {s.embedding_provider.value}")
    typer.echo(f"embedding_model    = {s.embedding_model_id}")
    typer.echo(f"collection         = {s.collection_name}")
    typer.echo(f"chunk_size/overlap = {s.chunk_size}/{s.chunk_overlap}  top_k={s.top_k}")
    typer.echo(f"gemini_api_key set = {bool(s.gemini_api_key)}")
    typer.echo(f"fallback_enabled   = {s.fallback_enabled}")


def _todo(name: str, phase: int) -> None:
    typer.echo(f"'{name}' ainda não implementado — chega na Fase {phase}.")
    raise typer.Exit(code=1)


@app.command()
def ingest(path: str) -> None:
    """(Fase 1) Indexa uma pasta de documentos."""
    _todo("ingest", 1)


@app.command()
def search(query: str) -> None:
    """(Fase 2) Mostra os top-k trechos para uma pergunta."""
    _todo("search", 2)


@app.command()
def ask(query: str) -> None:
    """(Fase 3) Responde com base nos documentos, citando a fonte."""
    _todo("ask", 3)


@app.command("eval")
def eval_() -> None:
    """(Fase 5) Roda o golden set e reporta métricas."""
    _todo("eval", 5)


if __name__ == "__main__":
    app()
