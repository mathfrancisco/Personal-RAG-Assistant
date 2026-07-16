"""Modo 100% local: factories rejeitam nuvem + pipeline não abre socket externo."""

import socket

import pytest

from rag_assistant.config.settings import Settings
from rag_assistant.domain.models import Answer, LLMResponse, RetrievedChunk
from rag_assistant.embeddings.factory import build_embedding_provider
from rag_assistant.llm.factory import build_llm
from rag_assistant.rag.pipeline import RAGPipeline

pytestmark = pytest.mark.local_only


def _local(**over) -> Settings:
    defaults = dict(
        rag_mode="local",
        llm_provider="ollama",
        embedding_provider="ollama",
        gemini_api_key="dummy",  # validador exige key p/ provider de nuvem
    )
    defaults.update(over)
    return Settings(**defaults)


def test_local_rejects_cloud_llm():
    s = _local(llm_provider="gemini")
    with pytest.raises(ValueError, match="modo local proíbe LLM"):
        build_llm(s)


def test_local_rejects_cloud_embedding():
    s = _local(embedding_provider="gemini")
    with pytest.raises(ValueError, match="modo local proíbe embedding"):
        build_embedding_provider(s)


class FakeRetriever:
    def retrieve(self, query, k=None):  # noqa: ARG002
        return [RetrievedChunk("t", "doc.txt", 0, 0.9)]


class FakeLLM:
    model_id = "fake"

    def generate(self, prompt):  # noqa: ARG002
        return LLMResponse(text="ok [1]", model=self.model_id)

    def stream(self, prompt):  # noqa: ARG002
        yield "ok [1]"


def test_pipeline_opens_no_external_socket(monkeypatch):
    """Com adapters fake, um ask() não deve abrir nenhuma conexão de rede."""

    def deny(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("modo local não pode abrir socket externo")

    monkeypatch.setattr(socket.socket, "connect", deny)
    ans = RAGPipeline(FakeRetriever(), FakeLLM()).ask("pergunta")
    assert isinstance(ans, Answer)
    assert "[1]" in ans.text
