"""Erros de domínio."""

from __future__ import annotations


class DomainError(Exception):
    """Base dos erros do projeto."""


class UnsupportedFormatError(DomainError):
    """Formato de arquivo não suportado pela ingestão."""


class DocumentLoadError(DomainError):
    """Falha ao ler/extrair texto de um documento."""


class EmbeddingMismatchError(DomainError):
    """O embedder configurado difere do modelo que gerou a coleção (SDD §5.6)."""
