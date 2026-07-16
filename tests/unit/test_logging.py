"""Logging estruturado: configura sem erro e emite eventos."""

from rag_assistant.observability.logging import configure_logging, get_logger


def test_configure_and_log(capsys):
    configure_logging(json_logs=True, level="INFO")
    log = get_logger("test")
    log.info("evento_teste", chave="valor")
    out = capsys.readouterr().out
    assert "evento_teste" in out
