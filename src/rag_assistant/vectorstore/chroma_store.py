"""VectorStore em ChromaDB (persistente, local).

A coleção é nomeada por modelo de embedding e guarda o modelo no metadado;
abrir com um embedder diferente levanta EmbeddingMismatchError (SDD §5.6).
"""

from __future__ import annotations

from rag_assistant.domain.exceptions import EmbeddingMismatchError
from rag_assistant.domain.models import EmbeddedChunk, RetrievedChunk

_NO_PAGE = -1


class ChromaVectorStore:
    def __init__(self, path: str, collection_name: str, embedding_model_id: str) -> None:
        import chromadb

        self._model = embedding_model_id
        client = chromadb.PersistentClient(path=path)
        self._col = client.get_or_create_collection(
            name=collection_name,
            metadata={"embedding_model": embedding_model_id, "hnsw:space": "cosine"},
        )
        stored = (self._col.metadata or {}).get("embedding_model")
        if stored and stored != embedding_model_id:
            raise EmbeddingMismatchError(
                f"coleção '{collection_name}' foi criada com '{stored}', "
                f"mas o embedder atual é '{embedding_model_id}'. Reindexe."
            )

    def upsert(self, chunks: list[EmbeddedChunk]) -> None:
        if not chunks:
            return
        self._col.upsert(
            ids=[c.chunk.id for c in chunks],
            embeddings=[c.vector for c in chunks],
            documents=[c.chunk.text for c in chunks],
            metadatas=[
                {
                    "source": c.chunk.source,
                    "chunk_index": c.chunk.chunk_index,
                    "page": c.chunk.page if c.chunk.page is not None else _NO_PAGE,
                    "doc_hash": c.chunk.doc_hash,
                }
                for c in chunks
            ],
        )

    def query(self, vector: list[float], k: int) -> list[RetrievedChunk]:
        res = self._col.query(
            query_embeddings=[vector],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]
        out: list[RetrievedChunk] = []
        for text, meta, dist in zip(docs, metas, dists, strict=True):
            page = meta.get("page", _NO_PAGE)
            out.append(
                RetrievedChunk(
                    text=text,
                    source=str(meta.get("source", "")),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    score=1.0 - float(dist),  # cosine distance -> similaridade
                    page=None if page == _NO_PAGE else int(page),
                )
            )
        return out

    def delete_by_source(self, source: str) -> None:
        self._col.delete(where={"source": source})

    def known_sources(self) -> dict[str, str]:
        got = self._col.get(include=["metadatas"])
        mapping: dict[str, str] = {}
        for meta in got.get("metadatas") or []:
            src = meta.get("source")
            if src is not None:
                mapping[str(src)] = str(meta.get("doc_hash", ""))
        return mapping
