"""Contrato do VectorStore contra Chroma real (persistente em tmp_path).

Cobre upsert → query → delete_by_source → known_sources e a proteção de
incompatibilidade de embedder (EmbeddingMismatchError, SDD §5.6).
"""

import pytest

from rag_assistant.domain.exceptions import EmbeddingMismatchError
from rag_assistant.domain.models import Chunk, EmbeddedChunk
from rag_assistant.vectorstore.chroma_store import ChromaVectorStore

MODEL = "fake-embed"


def _emb(text: str, source: str, idx: int, page=None) -> EmbeddedChunk:
    chunk = Chunk(text=text, source=source, chunk_index=idx, doc_hash="h1", page=page)
    # vetor 2D determinístico só para exercitar o store
    vector = [float(len(text)), float(idx)]
    return EmbeddedChunk(chunk=chunk, vector=vector)


def _store(tmp_path, model=MODEL) -> ChromaVectorStore:
    return ChromaVectorStore(str(tmp_path / "chroma"), "chunks__test", model)


def test_upsert_then_query_returns_chunk(tmp_path):
    store = _store(tmp_path)
    store.upsert([_emb("alpha", "a.txt", 0), _emb("beta longa", "a.txt", 1, page=2)])

    hits = store.query([9.0, 1.0], k=2)
    assert len(hits) == 2
    assert {h.source for h in hits} == {"a.txt"}
    assert all(isinstance(h.score, float) for h in hits)


def test_query_preserves_page_metadata(tmp_path):
    store = _store(tmp_path)
    store.upsert([_emb("com pagina", "doc.pdf", 0, page=3)])
    hits = store.query([10.0, 0.0], k=1)
    assert hits[0].page == 3


def test_delete_by_source_removes_only_that_source(tmp_path):
    store = _store(tmp_path)
    store.upsert([_emb("x", "a.txt", 0), _emb("y", "b.txt", 0)])
    store.delete_by_source("a.txt")
    assert set(store.known_sources()) == {"b.txt"}


def test_known_sources_maps_source_to_doc_hash(tmp_path):
    store = _store(tmp_path)
    store.upsert([_emb("x", "a.txt", 0)])
    assert store.known_sources() == {"a.txt": "h1"}


def test_reopen_with_different_model_raises(tmp_path):
    _store(tmp_path, model="model-A")
    with pytest.raises(EmbeddingMismatchError):
        _store(tmp_path, model="model-B")
