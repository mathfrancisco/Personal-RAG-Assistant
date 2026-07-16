"""Smoke do app Streamlit: executa o script headless (AppTest) sem exceção.

Não sobe navegador nem toca Ollama/rede — só garante que main() renderiza
(título, 3 abas, sidebar). Chroma/cache apontam para tmp_path via env.
"""

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_app_renders_without_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "cache"))
    monkeypatch.setenv("RAG_MODE", "local")

    at = AppTest.from_file(
        "src/rag_assistant/app/streamlit_app.py", default_timeout=60
    ).run()

    assert not at.exception
    assert at.title[0].value.endswith("Personal RAG Assistant")
    assert len(at.tabs) == 3
    assert at.sidebar.radio[0].label == "Modo"
