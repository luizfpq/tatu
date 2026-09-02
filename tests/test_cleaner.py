"""Testes de orquestracao (freeze + backup + remocao)."""

from __future__ import annotations

from pathlib import Path

from venv_tatu.cleaner import Action, Config, process
from venv_tatu.discovery import find_venvs


def _make_project(tmp_path: Path, pkgs: dict[str, str], name: str = "proj") -> Path:
    proj = tmp_path / name
    sp = proj / ".venv" / "lib" / "python3.11" / "site-packages"
    sp.mkdir(parents=True)
    (proj / ".venv" / "pyvenv.cfg").write_text("version = 3.11.5\n")
    for pk, ver in pkgs.items():
        (sp / f"{pk}-{ver}.dist-info").mkdir()
    return proj


def test_dry_run_does_not_touch_disk(tmp_path: Path):
    proj = _make_project(tmp_path, {"flask": "3.0.0"})
    venvs = list(find_venvs([tmp_path]))

    report = process(venvs, Config(dry_run=True))

    assert report.outcomes[0].action is Action.REMOVED  # relatado como removivel
    assert (proj / ".venv").exists()  # mas nada foi removido
    assert not (proj / "requirements.txt").exists()  # nem escrito


def test_apply_writes_requirements_and_removes(tmp_path: Path):
    proj = _make_project(tmp_path, {"flask": "3.0.0", "requests": "2.31.0"})
    venvs = list(find_venvs([tmp_path]))

    report = process(venvs, Config(dry_run=False))

    out = report.outcomes[0]
    assert out.action is Action.REMOVED
    assert not (proj / ".venv").exists()
    req = proj / "requirements.txt"
    assert req.exists()
    content = req.read_text()
    assert "flask==3.0.0" in content
    assert "requests==2.31.0" in content
    assert "# python do venv original: 3.11.5" in content


def test_backup_of_existing_requirements(tmp_path: Path):
    proj = _make_project(tmp_path, {"flask": "3.0.0"})
    req = proj / "requirements.txt"
    req.write_text("curado-a-mao==1.0\n")
    venvs = list(find_venvs([tmp_path]))

    process(venvs, Config(dry_run=False, backup_existing=True))

    bak = proj / "requirements.txt.bak"
    assert bak.exists()
    assert bak.read_text() == "curado-a-mao==1.0\n"


def test_no_remove_keeps_venv(tmp_path: Path):
    proj = _make_project(tmp_path, {"flask": "3.0.0"})
    venvs = list(find_venvs([tmp_path]))

    report = process(venvs, Config(dry_run=False, remove=False))

    assert report.outcomes[0].action is Action.FROZEN_ONLY
    assert (proj / ".venv").exists()
    assert (proj / "requirements.txt").exists()


def test_interactive_skip(tmp_path: Path):
    _make_project(tmp_path, {"flask": "3.0.0"})
    venvs = list(find_venvs([tmp_path]))

    report = process(venvs, Config(dry_run=False, confirm=lambda v: False))

    assert report.outcomes[0].action is Action.SKIPPED
    assert venvs[0].path.exists()


def test_empty_venv_fails_gracefully(tmp_path: Path):
    proj = tmp_path / "empty"
    (proj / ".venv" / "lib" / "python3.11" / "site-packages").mkdir(parents=True)
    (proj / ".venv" / "pyvenv.cfg").write_text("version = 3.11.5\n")
    venvs = list(find_venvs([tmp_path]))

    report = process(venvs, Config(dry_run=False))

    assert report.outcomes[0].action is Action.FAILED
    assert (proj / ".venv").exists()  # nao remove se nao conseguiu congelar
