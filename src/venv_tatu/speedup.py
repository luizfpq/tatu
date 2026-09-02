"""Acelerador opcional de descoberta via ``locate`` / ``plocate`` / ``mlocate``.

A varredura padrao usa ``os.walk``, que e confiavel mas percorre a arvore
inteira. Quando a maquina tem um banco ``locate`` que cobre os diretorios de
interesse, consultar o indice e muito mais rapido.

Cuidados tratados aqui:

- O banco pode estar desatualizado: todo caminho retornado e validado
  (o ``pyvenv.cfg`` precisa existir agora) e filtrado para dentro dos roots.
- Existem variantes (GNU findutils, mlocate, plocate) com flags distintas.
  Usamos apenas as portateis (``-b`` para basename, ``-i`` nao e preciso).
- Se o indice nao cobrir os roots (retorno vazio dentro do escopo), o
  chamador deve cair no ``os.walk``.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocateBackend:
    """Um binario 'locate' disponivel na maquina."""

    binary: str
    kind: str  # 'plocate' | 'mlocate' | 'findutils' | 'unknown'


def detect_locate() -> LocateBackend | None:
    """Detecta um binario locate utilizavel, preferindo plocate > mlocate > locate."""
    for name in ("plocate", "mlocate", "locate"):
        path = shutil.which(name)
        if not path:
            continue
        kind = _identify(path)
        # mlocate normalmente e invocado como 'locate'; plocate idem.
        return LocateBackend(binary=path, kind=kind)
    return None


def _identify(path: str) -> str:
    try:
        out = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=5
        ).stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if "plocate" in out:
        return "plocate"
    if "mlocate" in out:
        return "mlocate"
    if "findutils" in out:
        return "findutils"
    return "unknown"


def query_pyvenv(backend: LocateBackend, *, timeout: int = 30) -> list[Path]:
    """Consulta o banco por ``pyvenv.cfg``. Nao valida existencia (o chamador faz)."""
    # -b: casa apenas o basename. Portavel entre as variantes.
    cmd = [backend.binary, "-b", "pyvenv.cfg"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode not in (0, 1):  # 1 = sem resultados em algumas variantes
        return []
    results: list[Path] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.endswith("pyvenv.cfg"):
            results.append(Path(line))
    return results


def find_via_locate(
    backend: LocateBackend, roots: list[Path], *, timeout: int = 30
) -> list[Path] | None:
    """Devolve os pyvenv.cfg existentes sob ``roots`` segundo o indice locate.

    Retorna ``None`` quando o indice aparenta nao cobrir os roots (nenhum
    resultado dentro do escopo), sinalizando ao chamador que use o walk.
    Retorna uma lista (possivelmente vazia apos validacao) quando o indice
    cobre o escopo.
    """
    hits = query_pyvenv(backend, timeout=timeout)
    if not hits:
        return None

    norm_roots = [r.expanduser().resolve() for r in roots]
    in_scope = [h for h in hits if _under_any(h, norm_roots)]
    if not in_scope:
        # O banco tem pyvenv.cfg, mas nenhum dentro dos roots pedidos.
        # Pode ser cobertura parcial: melhor deixar o walk decidir.
        return None

    # valida existencia real (banco pode estar velho -> fantasmas)
    existing = [h for h in in_scope if h.is_file()]
    return existing


def _under_any(path: Path, roots: list[Path]) -> bool:
    try:
        rp = path.resolve()
    except OSError:
        rp = path
    for root in roots:
        try:
            rp.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def database_age_seconds(backend: LocateBackend) -> float | None:
    """Idade do banco de dados em segundos, se localizavel."""
    import time

    candidates = [
        "/var/lib/plocate/plocate.db",
        "/var/lib/mlocate/mlocate.db",
        "/var/cache/locate/locatedb",
        "/var/lib/locate/locatedb",
    ]
    for c in candidates:
        p = Path(c)
        if p.exists():
            try:
                return time.time() - p.stat().st_mtime
            except OSError:
                return None
    return None
