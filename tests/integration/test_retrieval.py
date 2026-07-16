"""Integração ingest → retrieve: o chunk esperado aparece no top-k.

Usa Chroma real (tmp_path) e um embedder fake determinístico — bag-of-words
projetado num espaço fixo, o bastante para que a similaridade de cosseno
recupere o trecho certo, sem depender de Ollama/rede.
"""

from rag_assistant.ingestion.pipeline import ingest_path
from rag_assistant.retrieval.retriever import Retriever
from rag_assistant.vectorstore.chroma_store import ChromaVectorStore

_VOCAB = ["contrato", "prazo", "entrega", "pagamento", "gato", "cachorro", "python", "cozinha"]


class BowEmbedder:
    """Embedding determinístico: contagem de palavras do vocabulário."""

    model_id = "bow-test"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)

    @staticmethod
    def _vec(text: str) -> list[float]:
        low = text.lower()
        return [float(low.count(w)) + 0.01 for w in _VOCAB]


def test_ingest_then_search_finds_expected_chunk(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "contrato.txt").write_text(
        "O prazo de entrega do contrato é de trinta dias após o pagamento.",
        encoding="utf-8",
    )
    (docs / "receita.txt").write_text(
        "Receita de cozinha: o gato e o cachorro não entram na cozinha.",
        encoding="utf-8",
    )

    store = ChromaVectorStore(str(tmp_path / "chroma"), "chunks__bow", "bow-test")
    embedder = BowEmbedder()
    ingest_path(
        docs,
        embedder=embedder,
        store=store,
        chunk_size=200,
        chunk_overlap=20,
        cache=None,
        log=lambda *_: None,
    )

    hits = Retriever(embedder, store, top_k=5).retrieve("Qual o prazo de entrega do contrato?")
    assert hits, "retrieval deve devolver algo"
    assert "contrato" in hits[0].source
    assert hits[0].score >= hits[-1].score  # ordenado por score desc
