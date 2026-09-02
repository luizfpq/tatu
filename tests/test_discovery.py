"""Testes de descoberta de venvs."""

from __future__ import annotations

from pathlib import Path

from venv_tatu.discovery import find_venvs


def _make_venv(project: Path, name: str = ".venv", version: str = "3.11.5") -> Path:
    venv = project / name
    (venv / "lib" / "python3.11" / "site-packages").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text(
        f"home = /usr/bin\nversion = {version}\nexecutable = /usr/bin/python3.11\n"
    )
    return venv


def test_finds_venv_by_pyvenv_cfg(tmp_path: Path):
    proj = tmp_path / "myproj"
    proj.mkdir()
    _make_venv(proj)

    venvs = list(find_venvs([tmp_path]))

    assert len(venvs) == 1
    assert venvs[0].project_dir == proj
    assert venvs[0].python_version == "3.11.5"


def test_detects_various_venv_names(tmp_path: Path):
    for name in (".venv", "venv", "env"):
        proj = tmp_path / f"proj_{name}"
        proj.mkdir()
        _make_venv(proj, name=name)

    venvs = list(find_venvs([tmp_path]))
    assert len(venvs) == 3


def test_does_not_descend_into_found_venv(tmp_path: Path):
    proj = tmp_path / "myproj"
    proj.mkdir()
    venv = _make_venv(proj)
    # venv aninhado dentro de site-packages nao deve ser reportado
    nested = venv / "lib" / "python3.11" / "site-packages" / "weird"
    nested.mkdir(parents=True)
    (nested / "pyvenv.cfg").write_text("version = 3.9.0\n")

    venvs = list(find_venvs([tmp_path]))
    assert len(venvs) == 1


def test_respects_ignores(tmp_path: Path):
    proj = tmp_path / ".cache" / "proj"
    proj.mkdir(parents=True)
    _make_venv(proj)

    venvs = list(find_venvs([tmp_path]))
    assert venvs == []


def test_missing_version_is_none(tmp_path: Path):
    proj = tmp_path / "p"
    proj.mkdir()
    venv = proj / ".venv"
    (venv / "lib" / "python3.11" / "site-packages").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr/bin\n")

    venvs = list(find_venvs([tmp_path]))
    assert len(venvs) == 1
    assert venvs[0].python_version is None
