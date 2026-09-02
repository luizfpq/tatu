"""Testes do acelerador locate (com validacao de escopo e fantasmas)."""

from __future__ import annotations

from pathlib import Path

from venv_tatu import speedup
from venv_tatu.speedup import LocateBackend


def _backend() -> LocateBackend:
    return LocateBackend(binary="/usr/bin/locate", kind="findutils")


def test_find_via_locate_filters_out_of_scope(tmp_path, monkeypatch):
    inside = tmp_path / "proj" / ".venv" / "pyvenv.cfg"
    inside.parent.mkdir(parents=True)
    inside.write_text("version = 3.11.0\n")
    outside = Path("/tmp/other/.venv/pyvenv.cfg")

    monkeypatch.setattr(
        speedup, "query_pyvenv", lambda backend, timeout=30: [inside, outside]
    )

    result = speedup.find_via_locate(_backend(), [tmp_path])
    assert result == [inside]


def test_find_via_locate_drops_ghosts(tmp_path, monkeypatch):
    # caminho dentro do escopo, mas que nao existe mais (banco velho)
    ghost = tmp_path / "gone" / ".venv" / "pyvenv.cfg"

    monkeypatch.setattr(
        speedup, "query_pyvenv", lambda backend, timeout=30: [ghost]
    )

    result = speedup.find_via_locate(_backend(), [tmp_path])
    # in-scope porem inexistente -> lista vazia (nao None, pois havia in-scope)
    assert result == []


def test_find_via_locate_returns_none_when_no_hits(monkeypatch):
    monkeypatch.setattr(speedup, "query_pyvenv", lambda backend, timeout=30: [])
    assert speedup.find_via_locate(_backend(), [Path("/whatever")]) is None


def test_find_via_locate_none_when_index_misses_roots(tmp_path, monkeypatch):
    # o banco tem entradas, mas nenhuma sob os roots pedidos
    elsewhere = Path("/opt/app/.venv/pyvenv.cfg")
    monkeypatch.setattr(
        speedup, "query_pyvenv", lambda backend, timeout=30: [elsewhere]
    )
    assert speedup.find_via_locate(_backend(), [tmp_path]) is None


def test_detect_locate_none_when_absent(monkeypatch):
    monkeypatch.setattr(speedup.shutil, "which", lambda name: None)
    assert speedup.detect_locate() is None


def test_discovery_use_locate_falls_back_to_walk(tmp_path, monkeypatch):
    # sem locate instalado, use_locate=True deve cair no walk e achar o venv
    from venv_tatu.discovery import find_venvs

    proj = tmp_path / "p"
    venv = proj / ".venv"
    (venv / "lib" / "python3.11" / "site-packages").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("version = 3.11.0\n")

    monkeypatch.setattr(speedup, "detect_locate", lambda: None)

    venvs = list(find_venvs([tmp_path], use_locate=True))
    assert len(venvs) == 1
    assert venvs[0].path == venv
