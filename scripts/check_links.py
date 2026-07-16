"""Verifica links relativos entre arquivos Markdown (após mover docs, nada quebrou).

Ignora links externos (http/https) e âncoras puras (#secao). Sai com código 1 se
algum alvo relativo não existir.

Uso:
    uv run python scripts/check_links.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_ROOT = Path(__file__).resolve().parent.parent


_SKIP = {".venv", "node_modules", ".git"}


def _iter_md() -> list[Path]:
    return [p for p in _ROOT.rglob("*.md") if _SKIP.isdisjoint(p.parts)]


def check() -> int:
    broken: list[str] = []
    for md in _iter_md():
        for target in _LINK.findall(md.read_text(encoding="utf-8")):
            target = target.strip()
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (md.parent / path_part).resolve()
            if not resolved.exists():
                rel = md.relative_to(_ROOT)
                broken.append(f"{rel}: link quebrado -> {target}")

    if broken:
        print("[FALHA] Links relativos quebrados:")
        for b in broken:
            print(f"   - {b}")
        return 1
    print(f"[OK] {len(_iter_md())} arquivos Markdown, nenhum link relativo quebrado.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
