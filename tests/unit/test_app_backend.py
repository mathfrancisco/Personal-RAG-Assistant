"""Helpers do frontend, testados sem subir o Streamlit."""

from rag_assistant.app.backend import (
    ChatHistory,
    provider_badge,
    resolve_settings,
    source_label,
)
from rag_assistant.config.settings import LLMProvider, RagMode
from rag_assistant.domain.models import RetrievedChunk


def test_resolve_settings_applies_sidebar_overrides():
    s = resolve_settings("local", "ollama")
    assert s.rag_mode is RagMode.local
    assert s.llm_provider is LLMProvider.ollama


def test_provider_badge_local_vs_hybrid():
    local = resolve_settings("local", "ollama")
    assert "local" in provider_badge(local)
    hybrid = resolve_settings("hybrid", "ollama")
    assert "hybrid" in provider_badge(hybrid)


def test_source_label_includes_page_and_score():
    chunk = RetrievedChunk("txt", "doc.pdf", 2, 0.87, page=4)
    label = source_label(chunk)
    assert "doc.pdf, p.4" in label
    assert "chunk #2" in label
    assert "0.87" in label


def test_chat_history_roundtrip():
    h = ChatHistory()
    h.add_user("oi")
    h.add_assistant("olá", sources=[RetrievedChunk("t", "s", 0, 0.5)])
    assert [m["role"] for m in h.messages] == ["user", "assistant"]
    assert len(h.messages[1]["sources"]) == 1
    h.clear()
    assert h.messages == []
