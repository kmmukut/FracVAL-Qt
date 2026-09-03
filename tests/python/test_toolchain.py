from __future__ import annotations

from pathlib import Path
import shutil
import sys

import pytest

from fracval import _toolchain


def _fake_compiler(directory: Path, name: str, banner: str) -> Path:
    """Create a runnable fake compiler that prints `banner` for --version."""
    if sys.platform == "win32":
        path = directory / f"{name}.bat"
        path.write_text(f"@echo {banner}\r\n", encoding="ascii")
    else:
        path = directory / name
        path.write_text(f"#!/bin/sh\necho '{banner}'\n", encoding="ascii")
        path.chmod(0o755)
    return path


def test_environment_variable_selects_fortran_compiler(tmp_path, monkeypatch):
    fake = _fake_compiler(tmp_path, "myfortran", "Fake Fortran 9.9")
    monkeypatch.setenv("FC", str(fake))
    tc = _toolchain.discover_toolchain()
    assert tc.fortran is not None
    assert tc.fortran.path == fake.resolve()
    assert tc.fortran.kind == "fortran"
    assert tc.fortran.version == "Fake Fortran 9.9"


def test_explicit_argument_beats_environment(tmp_path, monkeypatch):
    env_fake = _fake_compiler(tmp_path, "envcc", "Env C 1.0")
    arg_fake = _fake_compiler(tmp_path, "argcc", "Arg C 2.0")
    monkeypatch.setenv("CC", str(env_fake))
    tc = _toolchain.discover_toolchain(cc=str(arg_fake))
    assert tc.c is not None
    assert tc.c.path == arg_fake.resolve()
    assert tc.c.version == "Arg C 2.0"


def test_missing_compiler_reports_what_was_searched(monkeypatch):
    monkeypatch.setenv("FC", "definitely-not-a-compiler-xyz")
    monkeypatch.delenv("CC", raising=False)
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: None)
    tc = _toolchain.discover_toolchain()
    assert tc.fortran is None
    assert tc.c is None
    assert "definitely-not-a-compiler-xyz" in tc.searched
    assert "gfortran" in tc.searched


def test_conda_windows_directories_are_searched(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("CONDA_PREFIX", r"C:\envs\fracval")
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: None)
    tc = _toolchain.discover_toolchain()
    joined = "\n".join(tc.searched)
    assert "mingw-w64" in joined
    assert "Library" in joined


def test_install_hint_names_conda():
    hint = _toolchain.install_hint()
    assert "conda install" in hint


def test_is_msvc_detects_cl(tmp_path):
    cl = _toolchain.Compiler(kind="c", path=tmp_path / "cl.exe", version="MSVC")
    gcc = _toolchain.Compiler(kind="c", path=tmp_path / "gcc.exe", version="gcc 15")
    assert _toolchain.is_msvc(cl) is True
    assert _toolchain.is_msvc(gcc) is False
