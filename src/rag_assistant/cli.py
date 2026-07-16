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
    """Indexa uma pasta (ou arquivo) de documentos no vector store."""
    from rag_assistant.common.cache import EmbeddingCache
    from rag_assistant.embeddings.factory import build_embedding_provider
    from rag_assistant.ingestion.pipeline import ingest_path
    from rag_assistant.vectorstore.chroma_store import ChromaVectorStore

    s = get_settings()
    embedder = build_embedding_provider(s)
    store = ChromaVectorStore(s.chroma_path, s.collection_name, s.embedding_model_id)
    cache = EmbeddingCache(s.cache_path, s.embedding_model_id)
    typer.echo(
        f"Indexando '{path}' | embedder={s.embedding_model_id} | coleção={s.collection_name}"
    )
    try:
        report = ingest_path(
            path,
            embedder=embedder,
            store=store,
            chunk_size=s.chunk_size,
            chunk_overlap=s.chunk_overlap,
            cache=cache,
            log=typer.echo,
        )
    finally:
        cache.close()
    typer.echo(report.as_line())


@app.command()
def search(
    query: str,
    k: int = typer.Option(None, "--k", help="Nº de trechos (default: TOP_K da config)."),
) -> None:
    """Mostra os top-k trechos mais relevantes para uma pergunta (modo debug)."""
    from rag_assistant.embeddings.factory import build_embedding_provider
    from rag_assistant.retrieval.retriever import Retriever
    from rag_assistant.vectorstore.chroma_store import ChromaVectorStore

    s = get_settings()
    embedder = build_embedding_provider(s)
    store = ChromaVectorStore(s.chroma_path, s.collection_name, s.embedding_model_id)
    retriever = Retriever(embedder, store, s.top_k)

    hits = retriever.retrieve(query, k)
    if not hits:
        typer.echo("Nenhum trecho encontrado (índice vazio? rode `rag ingest`).")
        raise typer.Exit(code=1)

    for rank, h in enumerate(hits, start=1):
        loc = f"{h.source}" + (f", p.{h.page}" if h.page is not None else "")
        typer.echo(f"\n[{rank}] score={h.score:.3f} · {loc} · chunk #{h.chunk_index}")
        snippet = h.text.strip().replace("\n", " ")
        typer.echo(snippet[:300] + ("…" if len(snippet) > 300 else ""))


@app.command()
def ask(
    query: str,
    stream: bool = typer.Option(False, "--stream", help="Imprime a resposta token a token."),
    k: int = typer.Option(None, "--k", help="Nº de trechos de contexto (default: TOP_K)."),
) -> None:
    """Responde em linguagem natural, ancorado nos documentos e citando a fonte."""
    from rag_assistant.embeddings.factory import build_embedding_provider
    from rag_assistant.llm.factory import build_llm
    from rag_assistant.rag.citations import cited_sources
    from rag_assistant.rag.pipeline import RAGPipeline
    from rag_assistant.retrieval.retriever import Retriever
    from rag_assistant.vectorstore.chroma_store import ChromaVectorStore

    s = get_settings()
    embedder = build_embedding_provider(s)
    store = ChromaVectorStore(s.chroma_path, s.collection_name, s.embedding_model_id)
    retriever = Retriever(embedder, store, s.top_k)
    pipeline = RAGPipeline(retriever, build_llm(s))

    if stream:
        tokens, chunks = pipeline.ask_stream(query, k)
        buffer: list[str] = []
        for tok in tokens:
            buffer.append(tok)
            typer.echo(tok, nl=False)
        typer.echo("")
        sources = cited_sources("".join(buffer), chunks) if chunks else []
    else:
        answer = pipeline.ask(query, k)
        typer.echo(answer.text)
        sources = answer.sources

    if sources:
        typer.echo("\nFontes:")
        for i, src in enumerate(sources, start=1):
            loc = src.source + (f", p.{src.page}" if src.page is not None else "")
            typer.echo(f"  [{i}] {loc} · chunk #{src.chunk_index}")


@app.command("eval")
def eval_() -> None:
    """(Fase 5) Roda o golden set e reporta métricas."""
    _todo("eval", 5)


if __name__ == "__main__":
    app()
