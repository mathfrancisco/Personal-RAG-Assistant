"""Fragmentação de RawDocument em Chunks.

Usa `RecursiveCharacterTextSplitter` (respeita parágrafos/sentenças antes de cortar).
Nota V1: `chunk_size`/`chunk_overlap` são em CARACTERES (aproximação de tokens);
tokenização exata fica para uma iteração futura se o eval indicar necessidade.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag_assistant.domain.models import Chunk, RawDocument


def chunk_document(doc: RawDocument, *, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    parts = [p for p in splitter.split_text(doc.text) if p.strip()]
    return [
        Chunk(
            text=part,
            source=doc.source,
            chunk_index=i,
            doc_hash=doc.doc_hash,
            page=doc.page,
        )
        for i, part in enumerate(parts)
    ]
