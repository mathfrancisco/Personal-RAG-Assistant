import pytest

# Variáveis que poderiam vazar do ambiente real e mascarar os testes de config.
_ENV_KEYS = [
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "RAG_MODE",
    "LLM_PROVIDER",
    "EMBEDDING_PROVIDER",
]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Isola os testes de qualquer `.env`/variável de ambiente da máquina."""
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
