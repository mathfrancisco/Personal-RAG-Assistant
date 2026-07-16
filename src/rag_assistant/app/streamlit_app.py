"""Frontend Streamlit — chat RAG com citação, ingestão e métricas (placeholder).

Rodar:
    uv run streamlit run src/rag_assistant/app/streamlit_app.py
    # ou: streamlit run src/rag_assistant/app/streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

from rag_assistant.app.backend import (
    ChatHistory,
    build_pipeline,
    provider_badge,
    resolve_settings,
    source_label,
)

st.set_page_config(page_title="Personal RAG Assistant", page_icon="📚", layout="wide")


@st.cache_resource(show_spinner=False)
def _pipeline(mode: str, provider: str):
    """Objetos caros (Chroma/LLM) cacheados por (modo, provider) — evita rerun caro."""
    settings = resolve_settings(mode, provider)
    return build_pipeline(settings), settings


def _sidebar() -> tuple[str, str]:
    st.sidebar.header("⚙️ Configuração")
    mode = st.sidebar.radio("Modo", ["local", "hybrid"], help="local = 100% Ollama, offline")
    provider = st.sidebar.selectbox("LLM provider", ["ollama", "gemini"])
    st.sidebar.caption("Trocar aqui re-resolve a config sem reiniciar o app.")
    return mode, provider


def _chat_tab(pipeline, history: ChatHistory) -> None:
    for msg in history.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander(f"📎 {len(msg['sources'])} fonte(s)"):
                    for i, src in enumerate(msg["sources"], start=1):
                        st.markdown(f"**[{i}]** {source_label(src)}")
                        st.caption(src.text.strip()[:500])

    query = st.chat_input("Pergunte algo sobre seus documentos…")
    if not query:
        return

    history.add_user(query)
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        tokens, chunks = pipeline.ask_stream(query)
        text = st.write_stream(tokens)
        from rag_assistant.rag.citations import cited_sources

        sources = cited_sources(text, chunks) if chunks else []
        if sources:
            with st.expander(f"📎 {len(sources)} fonte(s)"):
                for i, src in enumerate(sources, start=1):
                    st.markdown(f"**[{i}]** {source_label(src)}")
                    st.caption(src.text.strip()[:500])
    history.add_assistant(text, sources)


def _ingest_tab(settings) -> None:
    st.subheader("📥 Ingestão")
    folder = st.text_input("Pasta de documentos", value="./data/documents")
    if st.button("Indexar", type="primary"):
        from rag_assistant.common.cache import EmbeddingCache
        from rag_assistant.embeddings.factory import build_embedding_provider
        from rag_assistant.ingestion.pipeline import ingest_path
        from rag_assistant.vectorstore.chroma_store import ChromaVectorStore

        embedder = build_embedding_provider(settings)
        store = ChromaVectorStore(
            settings.chroma_path, settings.collection_name, settings.embedding_model_id
        )
        cache = EmbeddingCache(settings.cache_path, settings.embedding_model_id)
        logs: list[str] = []
        with st.status("Indexando…", expanded=True) as status:
            try:
                report = ingest_path(
                    folder,
                    embedder=embedder,
                    store=store,
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap,
                    cache=cache,
                    log=logs.append,
                )
            finally:
                cache.close()
            for line in logs:
                st.write(line)
            status.update(label=report.as_line(), state="complete")


def _metrics_tab() -> None:
    st.subheader("📊 Métricas")
    st.info("Chega na Fase 5 — `rag eval` (Recall@5, tokens, custo, latência).")


def main() -> None:
    st.title("📚 Personal RAG Assistant")
    mode, provider = _sidebar()
    pipeline, settings = _pipeline(mode, provider)
    st.caption(provider_badge(settings))

    if "history" not in st.session_state:
        st.session_state.history = ChatHistory()
    history: ChatHistory = st.session_state.history

    chat, ingest, metrics = st.tabs(["💬 Chat", "📥 Ingestão", "📊 Métricas"])
    with chat:
        if st.button("🗑️ Limpar conversa"):
            history.clear()
        _chat_tab(pipeline, history)
    with ingest:
        _ingest_tab(settings)
    with metrics:
        _metrics_tab()


main()
