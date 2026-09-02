"""Testes do modulo de freeze, incluindo o fallback dist-info."""

from __future__ import annotations

from pathlib import Path

import pytest

from venv_tatu.freeze import (
    FreezeResult,
    freeze,
    freeze_via_distinfo,
    render,
)


def _make_site_packages(venv: Path, pyver: str = "3.11") -> Path:
    sp = venv / "lib" / f"python{pyver}" / "site-packages"
    sp.mkdir(parents=True)
    return sp


def _add_dist_info(sp: Path, name: str, version: str) -> None:
    (sp / f"{name}-{version}.dist-info").mkdir()


def test_distinfo_extracts_name_and_version(tmp_path: Path):
    venv = tmp_path / ".venv"
    sp = _make_site_packages(venv)
    _add_dist_info(sp, "requests", "2.31.0")
    _add_dist_info(sp, "charset_normalizer", "3.5.1")

    pkgs = freeze_via_distinfo(venv)

    assert pkgs == ["charset-normalizer==3.5.1", "requests==2.31.0"]


def test_distinfo_skips_base_packages_by_default(tmp_path: Path):
    venv = tmp_path / ".venv"
    sp = _make_site_packages(venv)
    _add_dist_info(sp, "pip", "24.0")
    _add_dist_info(sp, "setuptools", "69.0.0")
    _add_dist_info(sp, "flask", "3.0.0")

    pkgs = freeze_via_distinfo(venv)

    assert pkgs == ["flask==3.0.0"]


def test_distinfo_include_base(tmp_path: Path):
    venv = tmp_path / ".venv"
    sp = _make_site_packages(venv)
    _add_dist_info(sp, "pip", "24.0")

    pkgs = freeze_via_distinfo(venv, include_base=True)

    assert pkgs == ["pip==24.0"]


def test_distinfo_returns_none_when_empty(tmp_path: Path):
    venv = tmp_path / ".venv"
    _make_site_packages(venv)
    assert freeze_via_distinfo(venv) is None


def test_freeze_falls_back_to_distinfo_without_python(tmp_path: Path):
    # Sem bin/python, o pip nao roda; deve cair no dist-info.
    venv = tmp_path / ".venv"
    sp = _make_site_packages(venv)
    _add_dist_info(sp, "numpy", "2.0.0")

    result = freeze(venv)

    assert result is not None
    assert result.method == "dist-info"
    assert result.packages == ["numpy==2.0.0"]


def test_render_includes_header_and_version():
    result = FreezeResult(packages=["flask==3.0.0"], method="dist-info")
    out = render(result, python_version="3.11.5")

    assert "# gerado por tatu (metodo: dist-info)" in out
    assert "# python do venv original: 3.11.5" in out
    assert out.endswith("flask==3.0.0\n")


def test_egg_info_supported(tmp_path: Path):
    venv = tmp_path / ".venv"
    sp = _make_site_packages(venv)
    (sp / "legacy_pkg-1.2.3.egg-info").mkdir()

    pkgs = freeze_via_distinfo(venv)
    assert pkgs == ["legacy-pkg==1.2.3"]
