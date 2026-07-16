"""Pipeline de ingestão: load → (checar doc_hash) → chunk → embed(cache) → upsert.

Reindex incremental: arquivos com `doc_hash` inalterado são pulados; arquivos
novos/modificados têm os chunks antigos apagados e reindexados.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rag_assistant.domain.exceptions import DocumentLoadError, UnsupportedFormatError
from rag_assistant.domain.models import Chunk, EmbeddedChunk
from rag_assistant.domain.ports import EmbeddingProvider, VectorStore
from rag_assistant.ingestion.chunker import chunk_document
from rag_assistant.ingestion.loaders import SUPPORTED, load_document


@dataclass
class IngestReport:
    files_indexed: int = 0
    files_skipped: int = 0  # inalterados (incremental)
    files_failed: int = 0
    chunks_upserted: int = 0
    embeddings_from_cache: int = 0

    def as_line(self) -> str:
        return (
            f"{self.files_indexed} indexados, {self.files_skipped} inalterados, "
            f"{self.files_failed} com erro | {self.chunks_upserted} chunks "
            f"({self.embeddings_from_cache} embeddings do cache)"
        )


def _iter_files(root: str | Path):
    base = Path(root)
    if base.is_file():
        yield base
        return
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED:
            yield path


def _embed(
    chunks: list[Chunk], embedder: EmbeddingProvider, cache
) -> tuple[list[EmbeddedChunk], int]:
    """Embeda os chunks, aproveitando o cache; embeda em lote só os que faltam."""
    vectors: list[list[float] | None] = []
    misses_text: list[str] = []
    misses_idx: list[int] = []
    n_cached = 0

    for i, c in enumerate(chunks):
        cached = cache.get(c.text) if cache is not None else None
        if cached is not None:
            vectors.append(cached)
            n_cached += 1
        else:
            vectors.append(None)
            misses_text.append(c.text)
            misses_idx.append(i)

    if misses_text:
        fresh = embedder.embed_documents(misses_text)
        for j, i in enumerate(misses_idx):
            vectors[i] = fresh[j]
            if cache is not None:
                cache.put(chunks[i].text, fresh[j])

    embedded = [EmbeddedChunk(chunk=c, vector=v) for c, v in zip(chunks, vectors, strict=True)]
    return embedded, n_cached


def ingest_path(
    root: str | Path,
    *,
    embedder: EmbeddingProvider,
    store: VectorStore,
    chunk_size: int,
    chunk_overlap: int,
    cache=None,
    log=print,
) -> IngestReport:
    report = IngestReport()
    known = store.known_sources()

    for path in _iter_files(root):
        source = str(path)
        try:
            raw_docs = load_document(path)
        except UnsupportedFormatError:
            continue
        except DocumentLoadError as exc:
            report.files_failed += 1
            log(f"[erro] {path.name}: {exc}")
            continue

        doc_hash = raw_docs[0].doc_hash
        if known.get(source) == doc_hash:
            report.files_skipped += 1
            continue

        # novo ou modificado: remove versão antiga e reindexa
        store.delete_by_source(source)
        chunks: list[Chunk] = []
        for raw in raw_docs:
            chunks.extend(chunk_document(raw, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
        if not chunks:
            report.files_failed += 1
            log(f"[erro] {path.name}: sem texto para indexar")
            continue

        embedded, n_cached = _embed(chunks, embedder, cache)
        store.upsert(embedded)
        report.files_indexed += 1
        report.chunks_upserted += len(embedded)
        report.embeddings_from_cache += n_cached

    return report
