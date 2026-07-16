"""Integração da ingestão com fakes (sem Ollama/Chroma reais)."""

from rag_assistant.domain.models import Chunk, EmbeddedChunk, RetrievedChunk
from rag_assistant.ingestion.pipeline import _embed, ingest_path


class FakeEmbedder:
    model_id = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[float(len(t)), float(sum(map(ord, t)) % 97)] for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class FakeCache:
    def __init__(self) -> None:
        self._d: dict[str, list[float]] = {}

    def get(self, text: str):
        return self._d.get(text)

    def put(self, text: str, vector: list[float]) -> None:
        self._d[text] = vector


class FakeStore:
    def __init__(self) -> None:
        self.items: dict[str, EmbeddedChunk] = {}

    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        for c in chunks:
            self.items[c.chunk.id] = c

    def query(self, vector, k):  # noqa: ARG002 - não usado neste teste
        return [
            RetrievedChunk(c.chunk.text, c.chunk.source, c.chunk.chunk_index, 1.0)
            for c in list(self.items.values())[:k]
        ]

    def delete_by_source(self, source: str) -> None:
        self.items = {i: c for i, c in self.items.items() if c.chunk.source != source}

    def known_sources(self) -> dict[str, str]:
        return {c.chunk.source: c.chunk.doc_hash for c in self.items.values()}


def _ingest(root, store, cache=None):
    return ingest_path(
        root,
        embedder=FakeEmbedder(),
        store=store,
        chunk_size=100,
        chunk_overlap=10,
        cache=cache,
        log=lambda *_: None,
    )


def test_first_ingest_indexes_all(tmp_path):
    (tmp_path / "a.txt").write_text("conteúdo do arquivo A", encoding="utf-8")
    (tmp_path / "b.md").write_text("# B\ncorpo de B", encoding="utf-8")
    (tmp_path / "ignora.png").write_bytes(b"x")  # formato não suportado

    store = FakeStore()
    rep = _ingest(tmp_path, store)
    assert rep.files_indexed == 2
    assert rep.files_skipped == 0
    assert rep.chunks_upserted >= 2
    assert len(store.items) == rep.chunks_upserted


def test_rerun_is_incremental(tmp_path):
    (tmp_path / "a.txt").write_text("A", encoding="utf-8")
    store = FakeStore()
    _ingest(tmp_path, store)
    rep2 = _ingest(tmp_path, store)
    assert rep2.files_skipped == 1
    assert rep2.files_indexed == 0
    assert rep2.chunks_upserted == 0


def test_modified_file_is_reindexed(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("versão um", encoding="utf-8")
    store = FakeStore()
    _ingest(tmp_path, store)
    f.write_text("versão dois totalmente diferente", encoding="utf-8")
    rep = _ingest(tmp_path, store)
    assert rep.files_indexed == 1


def test_embed_uses_cache_on_second_pass():
    chunks = [Chunk(text=f"t{i}", source="s", chunk_index=i, doc_hash="h") for i in range(3)]
    emb = FakeEmbedder()
    cache = FakeCache()

    _, n1 = _embed(chunks, emb, cache)
    assert n1 == 0
    assert emb.calls == 1

    _, n2 = _embed(chunks, emb, cache)
    assert n2 == 3  # tudo veio do cache
    assert emb.calls == 1  # embedder não foi chamado de novo
