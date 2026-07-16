"""Template RAG: injeta contexto numerado + regras; citações mapeiam fontes."""

from rag_assistant.domain.models import RetrievedChunk
from rag_assistant.rag.citations import cited_sources
from rag_assistant.rag.prompts import build_prompt, format_context


def _chunks():
    return [
        RetrievedChunk("prazo é 30 dias", "contrato.pdf", 0, 0.9, page=3),
        RetrievedChunk("pagamento à vista", "contrato.pdf", 1, 0.8),
    ]


def test_context_is_numbered_with_source_and_page():
    ctx = format_context(_chunks())
    assert "[1] contrato.pdf, p.3:" in ctx
    assert "[2] contrato.pdf:" in ctx  # sem página quando page=None


def test_prompt_carries_rules_and_question():
    prompt = build_prompt("Qual o prazo?", _chunks())
    assert "SOMENTE com base no CONTEXTO" in prompt
    assert "Não encontrei essa informação nos documentos." in prompt
    assert "PERGUNTA: Qual o prazo?" in prompt
    assert "prazo é 30 dias" in prompt


def test_cited_sources_picks_referenced_numbers():
    chunks = _chunks()
    picked = cited_sources("O prazo é 30 dias [1].", chunks)
    assert len(picked) == 1
    assert picked[0].chunk_index == 0


def test_cited_sources_falls_back_to_all_when_uncited():
    chunks = _chunks()
    picked = cited_sources("resposta sem citar nada", chunks)
    assert picked == chunks
