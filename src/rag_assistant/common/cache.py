"""Cache de embedding em disco (SQLite via diskcache) — economiza quota/tempo.

Chave = modelo + hash do texto. Reingestão e reruns de eval não re-embeddam
o mesmo conteúdo. O modelo entra na chave porque vetores de modelos diferentes
não são intercambiáveis (SDD §5.6).
"""

from __future__ import annotations

import hashlib

import diskcache


class EmbeddingCache:
    def __init__(self, path: str, model: str) -> None:
        self._cache = diskcache.Cache(path)
        self._model = model

    def _key(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self._model}:{digest}"

    def get(self, text: str) -> list[float] | None:
        return self._cache.get(self._key(text))

    def put(self, text: str, vector: list[float]) -> None:
        self._cache.set(self._key(text), vector)

    def close(self) -> None:
        self._cache.close()


class ResponseCache:
    """Cache de respostas do LLM por chave já pronta (evita gastar quota em reruns).

    Usado pela avaliação: mesma pergunta+contexto+modelo → mesma resposta, zero
    chamadas novas no segundo run (determinismo do eval, SDD Fase 5).
    """

    def __init__(self, path: str) -> None:
        self._cache = diskcache.Cache(path)

    def get(self, key: str):
        return self._cache.get(key)

    def put(self, key: str, value) -> None:
        self._cache.set(key, value)

    def close(self) -> None:
        self._cache.close()
