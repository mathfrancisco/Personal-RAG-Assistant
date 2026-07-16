"""Tipos do domínio — sem I/O, sem dependência de framework."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RawDocument:
    """Texto extraído de um arquivo (uma página, no caso de PDF)."""

    text: str
    source: str  # caminho/nome do arquivo
    doc_hash: str  # SHA-256 do arquivo inteiro (detecta mudança p/ reindex)
    page: int | None = None
    file_type: str = ""


@dataclass(frozen=True, slots=True)
class Chunk:
    """Fragmento indexável de um documento."""

    text: str
    source: str
    chunk_index: int
    doc_hash: str
    page: int | None = None

    @property
    def id(self) -> str:
        """Id determinístico → reingestão sobrescreve o mesmo chunk."""
        return f"{self.source}::{self.page}::{self.chunk_index}"


@dataclass(frozen=True, slots=True)
class EmbeddedChunk:
    chunk: Chunk
    vector: list[float]


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    text: str
    source: str
    chunk_index: int
    score: float
    page: int | None = None
