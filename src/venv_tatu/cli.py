"""Interface de linha de comando do tatu."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .cleaner import Action, Config, Outcome, process
from .discovery import DEFAULT_IGNORES, Venv, find_venvs


def _human(size: int) -> str:
    val = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if val < 1024 or unit == "TB":
            return f"{val:.0f}{unit}" if unit == "B" else f"{val:.1f}{unit}"
        val /= 1024
    return f"{val:.1f}TB"


def _confirm_interactive(venv: Venv) -> bool:
    ver = venv.python_version or "?"
    size = _human(venv.size_bytes())
    prompt = f"  processar {venv.path}  (py {ver}, {size})? [s/N] "
    try:
        ans = input(prompt).strip().lower()
    except EOFError:
        return False
    return ans in ("s", "sim", "y", "yes")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tatu",
        description=(
            "Encontra virtualenvs, grava o requirements.txt de cada projeto "
            "e remove os venvs para liberar espaco."
        ),
    )
    p.add_argument(
        "roots",
        nargs="*",
        default=["."],
        help="diretorios para varrer (padrao: diretorio atual)",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="executa de fato (sem esta flag, roda em dry-run)",
    )
    p.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="pergunta a cada venv antes de agir",
    )
    p.add_argument(
        "--no-remove",
        action="store_true",
        help="apenas gera requirements, nao remove o venv",
    )
    p.add_argument(
        "--no-requirements",
        action="store_true",
        help="apenas remove o venv, nao gera requirements",
    )
    p.add_argument(
        "--no-backup",
        action="store_true",
        help="nao faz backup .bak de requirements existentes",
    )
    p.add_argument(
        "--include-base",
        action="store_true",
        help="inclui pip/setuptools/wheel no requirements",
    )
    p.add_argument(
        "--requirements-name",
        default="requirements.txt",
        help="nome do arquivo de saida (padrao: requirements.txt)",
    )
    p.add_argument(
        "--ignore",
        action="append",
        default=[],
        metavar="DIR",
        help="componente de caminho a ignorar (pode repetir)",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"tatu {__version__}",
    )
    return p


def _format_outcome(o: Outcome) -> str:
    tag = {
        Action.REMOVED: "REMOVIDO",
        Action.FROZEN_ONLY: "CONGELADO",
        Action.SKIPPED: "PULADO",
        Action.FAILED: "FALHOU",
    }[o.action]
    parts = [f"[{tag}] {o.venv.path}"]
    if o.freed_bytes:
        parts.append(f"({_human(o.freed_bytes)})")
    if o.method:
        parts.append(f"{o.package_count} pkgs via {o.method}")
    if o.detail:
        parts.append(f"- {o.detail}")
    return " ".join(parts)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    roots = [Path(r) for r in (args.roots or ["."])]
    ignores = DEFAULT_IGNORES + tuple(args.ignore)

    venvs = list(find_venvs(roots, ignores=ignores))
    if not venvs:
        print("Nenhum venv encontrado.")
        return 0

    dry = not args.apply
    if dry:
        print(f"[dry-run] {len(venvs)} venv(s) encontrado(s). "
              f"Use --apply para executar.\n")
    else:
        print(f"{len(venvs)} venv(s) encontrado(s).\n")

    cfg = Config(
        dry_run=dry,
        remove=not args.no_remove,
        write_requirements=not args.no_requirements,
        backup_existing=not args.no_backup,
        include_base=args.include_base,
        requirements_name=args.requirements_name,
        confirm=_confirm_interactive if args.interactive else None,
    )

    report = process(venvs, cfg)

    for o in report.outcomes:
        print(_format_outcome(o))

    freed = report.total_freed
    n_removed = len(report.removed)
    print()
    verb = "seria liberado" if dry else "liberado"
    print(f"Total: {n_removed} venv(s), {_human(freed)} {verb}.")
    if dry:
        print("Nada foi alterado (dry-run). Rode com --apply para aplicar.")

    failed = [o for o in report.outcomes if o.action is Action.FAILED]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
