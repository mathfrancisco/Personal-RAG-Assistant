"""friendly_errors: mapeia falhas comuns para códigos de saída claros."""

import typer

from rag_assistant.cli import friendly_errors
from rag_assistant.common.ratelimit import RateLimitError
from rag_assistant.domain.exceptions import DocumentLoadError, EmbeddingMismatchError


def _run(exc):
    @friendly_errors
    def cmd():
        raise exc

    try:
        cmd()
    except typer.Exit as e:
        return e.exit_code
    return 0


def test_mismatch_exits_2():
    assert _run(EmbeddingMismatchError("x")) == 2


def test_bad_document_exits_2():
    assert _run(DocumentLoadError("corrompido")) == 2


def test_rate_limit_exits_3():
    assert _run(RateLimitError("429")) == 3


def test_ollama_offline_exits_3():
    assert _run(ConnectionError("connection refused on 11434")) == 3


def test_generic_error_exits_1():
    assert _run(RuntimeError("algo inesperado")) == 1


def test_typer_exit_passes_through():
    # um Exit "de sucesso" (código 0) não deve virar erro
    assert _run(typer.Exit(code=0)) == 0
