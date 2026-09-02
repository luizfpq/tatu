"""Orquestracao: para cada venv, gera requirements e remove o venv."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from .discovery import Venv
from .freeze import freeze, render


class Action(Enum):
    REMOVED = "removed"
    FROZEN_ONLY = "frozen-only"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class Outcome:
    venv: Venv
    action: Action
    freed_bytes: int = 0
    requirements: Path | None = None
    package_count: int = 0
    method: str | None = None
    detail: str = ""


@dataclass
class Config:
    dry_run: bool = True
    remove: bool = True
    write_requirements: bool = True
    backup_existing: bool = True
    include_base: bool = False
    requirements_name: str = "requirements.txt"
    # Callback (venv) -> bool: decide se processa este venv (modo interativo).
    confirm: Callable[[Venv], bool] | None = None


@dataclass
class Report:
    outcomes: list[Outcome] = field(default_factory=list)

    @property
    def total_freed(self) -> int:
        return sum(o.freed_bytes for o in self.outcomes)

    @property
    def removed(self) -> list[Outcome]:
        return [o for o in self.outcomes if o.action is Action.REMOVED]

    def add(self, outcome: Outcome) -> None:
        self.outcomes.append(outcome)


def _backup(req: Path) -> Path | None:
    if not req.exists():
        return None
    bak = req.with_suffix(req.suffix + ".bak")
    shutil.copy2(req, bak)
    return bak


def process_one(venv: Venv, cfg: Config) -> Outcome:
    if cfg.confirm is not None and not cfg.confirm(venv):
        return Outcome(venv=venv, action=Action.SKIPPED, detail="usuario pulou")

    req_path = venv.project_dir / cfg.requirements_name

    if cfg.write_requirements:
        result = freeze(venv.path, include_base=cfg.include_base)
        if result is None:
            return Outcome(
                venv=venv,
                action=Action.FAILED,
                detail="nenhum pacote detectavel (freeze falhou)",
            )
        content = render(result, python_version=venv.python_version)
        if not cfg.dry_run:
            if cfg.backup_existing:
                _backup(req_path)
            req_path.write_text(content, encoding="utf-8")
        method = result.method
        count = result.count
    else:
        method = None
        count = 0

    if not cfg.remove:
        return Outcome(
            venv=venv,
            action=Action.FROZEN_ONLY,
            requirements=req_path if cfg.write_requirements else None,
            package_count=count,
            method=method,
        )

    size = venv.size_bytes()
    if not cfg.dry_run:
        shutil.rmtree(venv.path, ignore_errors=False)
        if venv.path.exists():
            return Outcome(
                venv=venv, action=Action.FAILED, detail="falha ao remover diretorio"
            )

    return Outcome(
        venv=venv,
        action=Action.REMOVED,
        freed_bytes=size,
        requirements=req_path if cfg.write_requirements else None,
        package_count=count,
        method=method,
    )


def process(venvs: list[Venv], cfg: Config) -> Report:
    report = Report()
    for venv in venvs:
        report.add(process_one(venv, cfg))
    return report
