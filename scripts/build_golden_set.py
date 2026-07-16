"""Valida (e ajuda a montar) o golden set de avaliação.

O golden set é específico do SEU corpus (`data/documents/`). Este script não
inventa perguntas: ele valida o schema de `evaluation/golden_set.json` e reporta
cobertura (nº de perguntas, quantas são out-of-corpus). Edite o JSON à mão,
apontando `expected_source` para um trecho do nome do arquivo esperado.

Uso:
    uv run python scripts/build_golden_set.py [caminho.json]
"""

from __future__ import annotations

import sys

from rag_assistant.evaluation.evaluator import load_golden_set

_MIN_RECOMMENDED = 30


def main(path: str = "evaluation/golden_set.json") -> int:
    items = load_golden_set(path)
    in_corpus = [i for i in items if not i.out_of_corpus]
    out_corpus = [i for i in items if i.out_of_corpus]

    missing_src = [i.question for i in in_corpus if not i.expected_source]
    print(
        f"Golden set: {len(items)} perguntas ({len(in_corpus)} no corpus, "
        f"{len(out_corpus)} fora do corpus)."
    )
    if missing_src:
        print(f"[AVISO] {len(missing_src)} perguntas do corpus sem `expected_source`:")
        for q in missing_src:
            print(f"   - {q}")
        return 1
    if len(items) < _MIN_RECOMMENDED:
        print(
            f"[INFO] Recomendado >= {_MIN_RECOMMENDED} perguntas (SDD Fase 5); atual: {len(items)}."
        )
    print("[OK] Schema valido.")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
