"""CLI do Personal RAG Assistant."""

from __future__ import annotations

import functools

import typer

from rag_assistant.config.settings import get_settings

app = typer.Typer(
    add_completion=False,
    help="Personal RAG Assistant — RAG local com citação de fontes, custo $0.",
)


def friendly_errors(fn):
    """Converte falhas comuns em mensagens claras (sem despejar traceback)."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        from rag_assistant.common.ratelimit import is_rate_limit_error
        from rag_assistant.domain.exceptions import DocumentLoadError, EmbeddingMismatchError

        try:
            return fn(*args, **kwargs)
        except typer.Exit:
            raise
        except EmbeddingMismatchError as exc:
            typer.secho(f"Erro de embedding: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc
        except (DocumentLoadError, FileNotFoundError) as exc:
            typer.secho(f"Documento/caminho inválido: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=2) from exc
        except Exception as exc:  # noqa: BLE001 - último recurso: mensagem amigável
            if is_rate_limit_error(exc):
                typer.secho(
                    "Quota do free tier esgotada (429). Tente mais tarde ou use RAG_MODE=local.",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                raise typer.Exit(code=3) from exc
            msg = str(exc).lower()
            if "connection" in msg or "refused" in msg or "11434" in msg:
                typer.secho(
                    "Não consegui falar com o Ollama. Rode `make ollama-up` "
                    "(ou verifique OLLAMA_BASE_URL).",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                raise typer.Exit(code=3) from exc
            typer.secho(f"Erro: {exc}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

    return wrapper


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


@app.command()
@friendly_errors
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
@friendly_errors
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
@friendly_errors
def ask(
    query: str,
    stream: bool = typer.Option(False, "--stream", help="Imprime a resposta token a token."),
    k: int = typer.Option(None, "--k", help="Nº de trechos de contexto (default: TOP_K)."),
) -> None:
    """Responde em linguagem natural, ancorado nos documentos e citando a fonte."""
    from rag_assistant.embeddings.factory import build_embedding_provider
    from rag_assistant.llm.factory import build_llm
    from rag_assistant.observability.tracer import build_tracer
    from rag_assistant.rag.citations import cited_sources
    from rag_assistant.rag.pipeline import RAGPipeline
    from rag_assistant.retrieval.retriever import Retriever
    from rag_assistant.vectorstore.chroma_store import ChromaVectorStore

    s = get_settings()
    embedder = build_embedding_provider(s)
    store = ChromaVectorStore(s.chroma_path, s.collection_name, s.embedding_model_id)
    retriever = Retriever(embedder, store, s.top_k)
    pipeline = RAGPipeline(retriever, build_llm(s), tracer=build_tracer(s))

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
@friendly_errors
def eval_(
    golden: str = typer.Option(None, "--golden", help="Caminho do golden set JSON."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Ignora o cache de respostas."),
) -> None:
    """Roda o golden set e gera report.md/report.json (Recall@k, tokens, custo, latência)."""
    from rag_assistant.common.cache import ResponseCache
    from rag_assistant.embeddings.factory import build_embedding_provider
    from rag_assistant.evaluation.evaluator import evaluate, load_golden_set
    from rag_assistant.evaluation.report import to_markdown, write_reports
    from rag_assistant.llm.factory import build_llm
    from rag_assistant.vectorstore.chroma_store import ChromaVectorStore

    s = get_settings()
    items = load_golden_set(golden or s.golden_set_path)
    embedder = build_embedding_provider(s)
    store = ChromaVectorStore(s.chroma_path, s.collection_name, s.embedding_model_id)
    llm = build_llm(s)
    cache = None if no_cache else ResponseCache(s.answer_cache_path)
    typer.echo(f"Avaliando {len(items)} perguntas | modelo={llm.model_id} | k={s.top_k}")
    try:
        report = evaluate(
            items,
            embedder=embedder,
            store=store,
            llm=llm,
            k=s.top_k,
            provider=s.llm_provider.value,
            answer_cache=cache,
        )
    finally:
        if cache is not None:
            cache.close()

    md_path, json_path = write_reports(report, s.eval_report_dir)
    typer.echo("")
    typer.echo(to_markdown(report))
    typer.echo(f"Relatórios salvos: {md_path} · {json_path}")


if __name__ == "__main__":
    app()
