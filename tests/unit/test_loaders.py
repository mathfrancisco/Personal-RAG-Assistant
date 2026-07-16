import pytest

from rag_assistant.domain.exceptions import UnsupportedFormatError
from rag_assistant.ingestion.loaders import load_document


def test_load_txt(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("olá mundo", encoding="utf-8")
    docs = load_document(f)
    assert len(docs) == 1
    assert docs[0].text == "olá mundo"
    assert docs[0].source == str(f)
    assert docs[0].page is None
    assert len(docs[0].doc_hash) == 64  # sha-256 hex


def test_load_md(tmp_path):
    f = tmp_path / "notas.md"
    f.write_text("# título\n\ncorpo", encoding="utf-8")
    docs = load_document(f)
    assert "título" in docs[0].text


def test_doc_hash_is_stable(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("conteúdo", encoding="utf-8")
    assert load_document(f)[0].doc_hash == load_document(f)[0].doc_hash


def test_doc_hash_changes_with_content(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("um", encoding="utf-8")
    h1 = load_document(f)[0].doc_hash
    f.write_text("outro", encoding="utf-8")
    h2 = load_document(f)[0].doc_hash
    assert h1 != h2


def test_unsupported_format_raises(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"\x89PNG")
    with pytest.raises(UnsupportedFormatError):
        load_document(f)
