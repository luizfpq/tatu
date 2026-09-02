"""Geracao de requirements a partir de um venv.

Estrategia em dois niveis:

1. ``<venv>/bin/python -m pip freeze`` (ou ``Scripts`` no Windows).
2. Fallback: le os diretorios ``*.dist-info`` / ``*.egg-info`` do
   site-packages e extrai ``nome==versao``.

O fallback e essencial para venvs sincronizados (Google Drive, Dropbox,
etc.) cujo interpretador quebrou: os metadados dos pacotes continuam no
disco mesmo quando o pip nao roda mais.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Pacotes de infraestrutura que nao entram no requirements por padrao.
_BASE_PACKAGES = {"pip", "setuptools", "wheel", "pkg-resources", "distribute"}

_DISTINFO_RE = re.compile(r"^(?P<name>.+?)-(?P<ver>[^-]+)\.(dist|egg)-info$")


@dataclass
class FreezeResult:
    packages: list[str]
    """Linhas no formato ``nome==versao``, ordenadas."""

    method: str
    """'pip' ou 'dist-info'."""

    @property
    def count(self) -> int:
        return len(self.packages)


def _python_bin(venv: Path) -> Path | None:
    for candidate in (
        venv / "bin" / "python",
        venv / "bin" / "python3",
        venv / "Scripts" / "python.exe",
    ):
        if candidate.exists():
            return candidate
    return None


def _site_packages(venv: Path) -> list[Path]:
    dirs: list[Path] = []
    for pat in ("lib/python*/site-packages", "lib64/python*/site-packages", "Lib/site-packages"):
        dirs.extend(venv.glob(pat))
    return dirs


def freeze_via_pip(venv: Path, *, timeout: int = 60) -> list[str] | None:
    py = _python_bin(venv)
    if py is None:
        return None
    try:
        proc = subprocess.run(
            [str(py), "-m", "pip", "freeze", "--all"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    lines = []
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" in line or line.startswith("-e "):
            lines.append(line)
    return lines or None


def freeze_via_distinfo(venv: Path, *, include_base: bool = False) -> list[str] | None:
    found: dict[str, str] = {}
    for sp in _site_packages(venv):
        if not sp.is_dir():
            continue
        for entry in sp.iterdir():
            m = _DISTINFO_RE.match(entry.name)
            if not m:
                continue
            name = m.group("name").replace("_", "-").lower()
            if not include_base and name in _BASE_PACKAGES:
                continue
            found[name] = m.group("ver")
    if not found:
        return None
    return [f"{n}=={v}" for n, v in sorted(found.items())]


def freeze(venv: Path, *, include_base: bool = False) -> FreezeResult | None:
    """Congela o venv, tentando pip e caindo no fallback dist-info."""
    pkgs = freeze_via_pip(venv)
    if pkgs is not None:
        if not include_base:
            pkgs = [
                p
                for p in pkgs
                if p.split("==")[0].replace("_", "-").lower() not in _BASE_PACKAGES
            ]
        return FreezeResult(packages=pkgs, method="pip")
    pkgs = freeze_via_distinfo(venv, include_base=include_base)
    if pkgs is not None:
        return FreezeResult(packages=pkgs, method="dist-info")
    return None


def render(result: FreezeResult, *, python_version: str | None = None) -> str:
    """Monta o conteudo do requirements.txt com cabecalho informativo."""
    header = [f"# gerado por tatu (metodo: {result.method})"]
    if python_version:
        header.append(f"# python do venv original: {python_version}")
    body = "\n".join(result.packages)
    return "\n".join(header) + "\n" + body + ("\n" if body else "")
