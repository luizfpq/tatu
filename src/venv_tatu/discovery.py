"""Descoberta de virtualenvs.

Um venv e identificado de forma confiavel pela presenca de um arquivo
``pyvenv.cfg`` na sua raiz (PEP 405). Nao dependemos do nome da pasta
(venv, .venv, env, ...), que e apenas convencao.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# Diretorios que nunca devem ser varridos (caches de ferramentas, etc.).
DEFAULT_IGNORES: tuple[str, ...] = (
    ".cache",
    ".local/share",
    ".config",
    ".vscode",
    ".vscode-server",
    ".cursor",
    ".kiro",
    "node_modules",
    ".git",
)


@dataclass(frozen=True)
class Venv:
    """Um virtualenv encontrado no disco."""

    path: Path
    """Raiz do venv (diretorio que contem o pyvenv.cfg)."""

    project_dir: Path
    """Diretorio do projeto (pai do venv), onde o requirements sera gravado."""

    python_version: str | None
    """Versao do Python declarada no pyvenv.cfg, ex. '3.13.5'. None se ausente."""

    def size_bytes(self) -> int:
        total = 0
        for p in self.path.rglob("*"):
            try:
                if p.is_file() and not p.is_symlink():
                    total += p.stat().st_size
            except OSError:
                continue
        return total


def _read_version(cfg: Path) -> str | None:
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r"^version\s*=\s*(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    # Alguns venvs usam "version_info".
    m = re.search(r"^version_info\s*=\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _is_ignored(path: Path, roots: list[Path], ignores: tuple[str, ...]) -> bool:
    for root in roots:
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        parts = set(rel.parts)
        for ig in ignores:
            ig_parts = Path(ig).parts
            # ignora se qualquer subsequencia de componentes casar
            if ig_parts and _contains_subseq(rel.parts, ig_parts):
                return True
            if len(ig_parts) == 1 and ig in parts:
                return True
    return False


def _contains_subseq(parts: tuple[str, ...], sub: tuple[str, ...]) -> bool:
    n, m = len(parts), len(sub)
    if m == 0 or m > n:
        return False
    for i in range(n - m + 1):
        if parts[i : i + m] == sub:
            return True
    return False


def find_venvs(
    roots: list[Path],
    ignores: tuple[str, ...] = DEFAULT_IGNORES,
) -> Iterator[Venv]:
    """Percorre ``roots`` e devolve um :class:`Venv` para cada pyvenv.cfg.

    Nao entra dentro de um venv ja encontrado (evita falsos positivos de
    venvs aninhados dentro de site-packages).
    """
    seen: list[Path] = []
    for root in roots:
        root = root.expanduser().resolve()
        if not root.exists():
            continue
        for cfg in _walk_pyvenv(root, ignores, seen):
            venv_path = cfg.parent
            yield Venv(
                path=venv_path,
                project_dir=venv_path.parent,
                python_version=_read_version(cfg),
            )
            seen.append(venv_path)


def _walk_pyvenv(
    root: Path, ignores: tuple[str, ...], seen: list[Path]
) -> Iterator[Path]:
    import os

    root_list = [root]
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        # nao descer em venvs ja encontrados
        if any(_is_within(here, s) for s in seen):
            dirnames[:] = []
            continue
        if _is_ignored(here, root_list, ignores):
            dirnames[:] = []
            continue
        if "pyvenv.cfg" in filenames:
            yield here / "pyvenv.cfg"
            # nao precisamos descer mais nesse ramo
            dirnames[:] = []


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False
