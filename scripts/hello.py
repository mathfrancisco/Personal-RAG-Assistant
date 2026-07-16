"""Fase 0 — prova que o LLM primário (Ollama) responde, e o fallback (Gemini) se houver key.

Uso:
    uv run python scripts/hello.py

Requer o Ollama rodando (Docker: `make ollama-up && make ollama-pull`).
GEMINI_API_KEY é opcional — só para testar o fallback.
"""

from __future__ import annotations

import sys

from rag_assistant.config.settings import get_settings

PROMPT = "Responda em uma frase curta: o que é RAG (Retrieval-Augmented Generation)?"


def _try(name: str, build) -> None:
    try:
        model = build()
        resp = model.invoke(PROMPT)
        text = getattr(resp, "content", str(resp))
        print(f"\n=== {name} ===\n{text.strip()}")
    except Exception as exc:  # noqa: BLE001 - smoke: queremos ver qualquer falha
        print(f"\n=== {name} ===\n[falhou] {type(exc).__name__}: {exc}")


def main() -> int:
    s = get_settings()
    print(f"Prompt: {PROMPT}")

    def ollama():
        from langchain_ollama import ChatOllama

        return ChatOllama(model=s.ollama_llm_model, base_url=s.ollama_base_url, temperature=0)

    def gemini():
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=s.gemini_llm_model, google_api_key=s.gemini_api_key, temperature=0
        )

    _try(f"Ollama (primário · {s.ollama_llm_model})", ollama)
    if s.gemini_api_key:
        _try("Gemini (fallback · free tier)", gemini)
    else:
        print("\n=== Gemini (fallback) ===\n[pulado] GEMINI_API_KEY não definido (roda 100% local)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
