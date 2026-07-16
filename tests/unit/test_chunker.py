from rag_assistant.domain.models import RawDocument
from rag_assistant.ingestion.chunker import chunk_document


def _doc(text: str) -> RawDocument:
    return RawDocument(text=text, source="a.txt", doc_hash="h", page=3, file_type=".txt")


def test_splits_long_text_into_multiple_chunks():
    text = " ".join(f"palavra{i}" for i in range(200))
    chunks = chunk_document(_doc(text), chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1


def test_chunk_indices_are_sequential_and_metadata_preserved():
    text = "a" * 500
    chunks = chunk_document(_doc(text), chunk_size=100, chunk_overlap=10)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(c.source == "a.txt" and c.doc_hash == "h" and c.page == 3 for c in chunks)


def test_short_text_single_chunk():
    chunks = chunk_document(_doc("curto"), chunk_size=100, chunk_overlap=10)
    assert len(chunks) == 1
    assert chunks[0].id == "a.txt::3::0"
