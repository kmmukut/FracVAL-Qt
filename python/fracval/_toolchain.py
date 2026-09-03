"""Compiler discovery shared by tools/build.py and fracval-info.

Standard library only: this module must import without NumPy so the standalone
executable can be built in an environment that has no Python packages yet.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig

_FORTRAN_NAMES = ("gfortran", "x86_64-w64-mingw32-gfortran")
_C_NAMES = ("gcc", "x86_64-w64-mingw32-gcc")


@dataclass(frozen=True)
class Compiler:
    kind: str
    path: Path
    version: str


@dataclass(frozen=True)
class Toolchain:
    fortran: Compiler | None
    c: Compiler | None
    searched: tuple[str, ...]


def _conda_windows_dirs() -> list[Path]:
    """MinGW toolchain directories inside an active conda env on Windows."""
    prefix = os.environ.get("CONDA_PREFIX")
    if not prefix or sys.platform != "win32":
        return []
    base = Path(prefix)
    return [base / "Library" / "mingw-w64" / "bin", base / "Library" / "bin"]


def _version_banner(path: Path) -> str:
    try:
        proc = subprocess.run(
            [str(path), "--version"], capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    lines = (proc.stdout or proc.stderr).strip().splitlines()
    return lines[0].strip() if lines else "unknown"


def _find(kind: str, explicit: str | None, env_var: str, names: tuple[str, ...],
          searched: list[str]) -> Compiler | None:
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    env_value = os.environ.get(env_var)
    if env_value:
        candidates.append(env_value)
    if kind == "c" and sys.platform != "win32":
        configured = sysconfig.get_config_var("CC")
        if configured:
            candidates.append(configured.split()[0])
    candidates.extend(names)

    for candidate in candidates:
        searched.append(candidate)
        found = shutil.which(candidate)
        if found:
            path = Path(found).resolve()
            return Compiler(kind, path, _version_banner(path))

    for directory in _conda_windows_dirs():
        for name in names:
            searched.append(str(directory / name))
            found = shutil.which(name, path=str(directory))
            if found:
                path = Path(found).resolve()
                return Compiler(kind, path, _version_banner(path))
    return None


def discover_toolchain(fc: str | None = None, cc: str | None = None) -> Toolchain:
    """Locate the Fortran and C compilers FracVAL should use.

    Search order for each compiler: explicit argument, environment variable
    (``FC`` / ``CC``), ``sysconfig`` (C compiler, POSIX only), well-known
    executable names on ``PATH``, then the MinGW directories of an active conda
    environment on Windows. Nothing is raised; callers inspect the result.
    """
    searched: list[str] = []
    fortran = _find("fortran", fc, "FC", _FORTRAN_NAMES, searched)
    c = _find("c", cc, "CC", _C_NAMES, searched)
    return Toolchain(fortran=fortran, c=c, searched=tuple(dict.fromkeys(searched)))


def is_msvc(compiler: Compiler) -> bool:
    """True when the C compiler is Microsoft ``cl``, which cannot link with gfortran."""
    return compiler.path.stem.lower() == "cl"


def install_hint() -> str:
    """One-line instruction for installing the expected toolchain on this OS."""
    if sys.platform == "win32":
        return "conda install -c conda-forge gfortran_win-64 gcc_win-64"
    if sys.platform == "darwin":
        return "conda install -c conda-forge gfortran c-compiler   (or: brew install gcc)"
    return "conda install -c conda-forge gfortran c-compiler   (or: sudo apt install gfortran gcc)"
