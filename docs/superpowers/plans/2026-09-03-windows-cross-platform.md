# Windows Cross-Platform Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make FracVAL-Qt build, test, and run on Windows (conda/miniforge + MinGW gfortran) with the same Python-driven commands as macOS and Linux, verified by a three-OS CI matrix.

**Architecture:** A stdlib-only compiler-discovery module (`python/fracval/_toolchain.py`) feeds a cross-platform build script (`tools/build.py`) that builds both the standalone executable and the F2PY extension. The Bash test harness becomes a pytest module, and all Python tests become pytest-discoverable so `pytest` is the one test command on every OS. The Makefile stays as a POSIX convenience wrapper that delegates the cross-platform steps to the Python tooling. Fortran numerics are untouched.

**Tech Stack:** Python 3.10+, NumPy F2PY (wrapper generation only, no Meson), gfortran/gcc (MinGW-w64 on Windows via conda-forge `gfortran_win-64`), PySide6 pip wheel, pytest, GitHub Actions with `conda-incubator/setup-miniconda`.

**Spec:** `docs/superpowers/specs/2026-09-03-windows-cross-platform-design.md`

## Global Constraints

- `requires-python = ">=3.10"`; no syntax or stdlib feature newer than 3.10 (so `tomllib` is not available; `ignore_cleanup_errors` is).
- Windows toolchain is MinGW-w64 gfortran + gcc only. MSVC `cl` must be rejected with a message. flang is out of scope.
- No change to any file in `src/` other than `ensure_output_directory` in `src/Ctes.f90`. Fixed-seed outputs must not change.
- Fortran compile order is fixed: `Ctes, random, RAND_SAMPLE, a_Random_PP, PCA_cca, PCA_Subclusters_module, Save_results_CC, CCA_module`, then `Frac_VAL_CCA` (exe) or `fracval_python_api` (ext).
- PySide6 is installed from pip on every OS; conda-forge PySide6 is never listed.
- Version becomes `1.1.0` in `pyproject.toml`, `python/fracval/__init__.py`, and `CITATION.cff`.
- Every new test must run under `pytest` from the repo root and skip (not fail) when a native artifact is not built.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01K1V4MVev8BtNPZ7X9RXC9e
  ```
- Local verification environment on the maintainer's macOS machine: the conda env `testbed` (`/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python`, Python 3.13, NumPy 2.2, PySide6 6.11, `fracval-qt` already installed editable). Homebrew `gfortran` 16 is on PATH. Use `PYTHON=/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python` for every command below; `pytest` is installed in Task 0.
- Do not push to GitHub without the maintainer's go-ahead; each task ends with a local commit.

## File map

| Path | Responsibility | Status |
|---|---|---|
| `environment.yml` | conda-forge env for macOS/Linux (compilers from conda-forge) | create |
| `environment-windows.yml` | same plus `gfortran_win-64`, `gcc_win-64` | create |
| `python/fracval/_toolchain.py` | stdlib-only compiler discovery: `discover_toolchain()`, `install_hint()` | create |
| `tools/build.py` | `exe`, `ext`, `all`, `clean` subcommands; single source list; Windows link rules; post-link import check | create |
| `python/build_fortran_extension.py` | two-line shim delegating to `tools/build.py ext` | rewrite |
| `python/fracval/diagnostics.py` | add compiler report | modify |
| `python/fracval/engine.py` | pre-create output dir; `CREATE_NO_WINDOW` | modify |
| `src/Ctes.f90` | backslash path for cmd.exe mkdir | modify |
| `python/fracval/desktop/qt_runtime.py` | `Lib/site-packages` fallback; `windows` platform pin; per-OS expected plugin | modify |
| `python/fracval/desktop/viewer.py` | `ignore_cleanup_errors=True` | modify |
| `tests/python/conftest.py` | GUI test opt-in; `build_tool` fixture | create |
| `tests/python/test_toolchain.py` | discovery tests | create |
| `tests/python/test_build_tool.py` | flag/link rule tests, Makefile manifest test | create |
| `tests/python/test_fortran_cli.py` | port of `tests/run_tests.sh` | create |
| `tests/run_tests.sh` | removed | delete |
| `tests/python/test_python_api.py`, `test_visualization.py`, `test_qt_runtime_paths.py`, `test_qt_gui.py` | pytest-shaped | modify |
| `tests/python/test_packaging.py` | version consistency | create |
| `pyproject.toml`, `setup.cfg` | pytest config, package-data, build_base, version | modify/create |
| `Makefile` | delegate cross-platform targets | modify |
| `.github/workflows/ci.yml` | linux-apt + conda-matrix jobs | modify |
| `README.md`, `doc/*.md`, `CONTRIBUTING.md`, `gui/README.md`, `examples/README.md`, `tests/README.md`, `doc/FracVAL_User_Developer_Guide.tex`, `CHANGELOG.md` | conda-first, per-OS instructions | modify |

---

### Task 0: Local prerequisites

**Files:** none committed.

- [ ] **Step 1: Install pytest into the testbed env and confirm the baseline builds**

Run:
```bash
PYTHON=/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python
$PYTHON -m pip install -e '.[dev]'
make FC=gfortran
make python-ext PYTHON=$PYTHON
$PYTHON -m fracval.diagnostics
```
Expected: `pytest` installs; `build/fracval` links; `python/fracval/_fracval_fortran.cpython-313-darwin.so` is rebuilt; diagnostics show `Available backends  : extension, executable`.

- [ ] **Step 2: Record the baseline fixed-seed outputs**

Run:
```bash
bash tests/run_tests.sh
cp tests/monodisperse/results/N_00000100_Agg_00000001.dat /private/tmp/claude-501/-Volumes-Mukut-Tweaks-git-repos-FracVAL-Qt/b4090149-80c7-4ac1-863c-f91792e63e32/scratchpad/baseline_mono.dat
cp tests/overlap_statistical/results/N_00000030_Agg_00000001.dat /private/tmp/claude-501/-Volumes-Mukut-Tweaks-git-repos-FracVAL-Qt/b4090149-80c7-4ac1-863c-f91792e63e32/scratchpad/baseline_stat.dat
```
Expected: `All FracVAL smoke tests passed.` The copies are compared against outputs at the end of Task 7 to prove the Fortran change did not alter geometry.

---

### Task 1: Environment files and CI toolchain probe

**Files:**
- Create: `environment.yml`
- Create: `environment-windows.yml`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: conda env name `fracval` used by all later docs and CI steps.

- [ ] **Step 1: Write `environment.yml`**

```yaml
# FracVAL-Qt development environment for macOS and Linux.
#   conda env create -f environment.yml
#   conda activate fracval
#   python -m pip install -e ".[gui,dev]"
#   python tools/build.py all
# Windows users: use environment-windows.yml instead.
name: fracval
channels:
  - conda-forge
dependencies:
  - python=3.12
  - numpy>=1.24
  - plotly>=5.18
  - pytest>=7
  - gfortran
  - c-compiler
  - pip
  - pip:
      - PySide6>=6.6
```

- [ ] **Step 2: Write `environment-windows.yml`**

```yaml
# FracVAL-Qt development environment for Windows (Miniforge/conda).
#   conda env create -f environment-windows.yml
#   conda activate fracval
#   python -m pip install -e ".[gui,dev]"
#   python tools/build.py all
# gfortran_win-64 and gcc_win-64 provide the MinGW-w64 GNU toolchain that
# tools/build.py expects. MSVC is not supported for the Fortran extension.
name: fracval
channels:
  - conda-forge
dependencies:
  - python=3.12
  - numpy>=1.24
  - plotly>=5.18
  - pytest>=7
  - gfortran_win-64
  - gcc_win-64
  - pip
  - pip:
      - PySide6>=6.6
```

- [ ] **Step 3: Add a probe job to CI**

Replace `.github/workflows/ci.yml` with:

```yaml
name: core-tests

on:
  push:
  pull_request:

jobs:
  linux-apt:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install GNU Fortran
        run: |
          sudo apt-get update
          sudo apt-get install -y gfortran

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e '.[dev]'

      - name: Build standalone Fortran generator
        # Treat free-form line truncation as an error so source remains portable
        # across GNU Fortran versions (Fortran free-form limit: 132 columns).
        run: make -j2 FFLAGS='-O2 -Werror=line-truncation'

      - name: Run deterministic Fortran/Python regression suite
        run: make test PYTHON=python

  conda-toolchain-probe:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-latest
            env-file: environment.yml
          - os: macos-latest
            env-file: environment.yml
          - os: windows-latest
            env-file: environment-windows.yml
    defaults:
      run:
        shell: bash -el {0}
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Miniforge environment
        uses: conda-incubator/setup-miniconda@v3
        with:
          miniforge-version: latest
          environment-file: ${{ matrix.env-file }}
          activate-environment: fracval
          auto-activate-base: false

      - name: Report toolchain
        run: |
          conda info
          conda list
          python --version
          gfortran --version
          gcc --version
          python -c "import numpy, plotly, PySide6; print(numpy.__version__, plotly.__version__, PySide6.__version__)"
```

- [ ] **Step 4: Validate YAML locally**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in ('environment.yml','environment-windows.yml','.github/workflows/ci.yml')]; print('ok')"`
Expected: `ok` (if PyYAML is missing, `pip install pyyaml` into testbed first).

- [ ] **Step 5: Commit**

```bash
git add environment.yml environment-windows.yml .github/workflows/ci.yml
git commit -m "Add conda environment files and a three-OS toolchain probe job"
```

- [ ] **Step 6: Verify the probe on GitHub**

Ask the maintainer to push (or push if they have said to). Open the Actions run and confirm the `windows-latest` probe prints a `GNU Fortran (...)` line and a `gcc (...)` line. If `gcc_win-64` is reported as an unknown package, replace it in `environment-windows.yml` with `mingw-w64-ucrt-x86_64-gcc` and re-run; if `gfortran_win-64` is unknown, use `m2w64-gcc-fortran` and `m2w64-gcc`. Record the final package names in the spec's section 9 item 1 and commit that edit.

---

### Task 2: Compiler discovery module and pytest scaffolding

**Files:**
- Create: `python/fracval/_toolchain.py`
- Create: `tests/python/conftest.py`
- Create: `tests/python/test_toolchain.py`
- Modify: `pyproject.toml` (add `[tool.pytest.ini_options]`)

**Interfaces:**
- Produces:
  - `fracval._toolchain.Compiler` dataclass: `kind: str`, `path: Path`, `version: str`
  - `fracval._toolchain.Toolchain` dataclass: `fortran: Compiler | None`, `c: Compiler | None`, `searched: tuple[str, ...]`
  - `fracval._toolchain.discover_toolchain(fc: str | None = None, cc: str | None = None) -> Toolchain`
  - `fracval._toolchain.install_hint() -> str`
  - `fracval._toolchain.is_msvc(compiler: Compiler) -> bool`

- [ ] **Step 1: Add pytest configuration to `pyproject.toml`**

Append to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests/python"]
pythonpath = ["python"]
addopts = "-ra"
```

- [ ] **Step 2: Write `tests/python/conftest.py`**

```python
"""pytest configuration shared by the FracVAL Python tests."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "python") not in sys.path:
    sys.path.insert(0, str(ROOT / "python"))

# The Qt construction smoke test needs PySide6 and a headless platform plugin.
# It stays opt-in so a plain `pytest` never fails on a machine without Qt.
collect_ignore = [] if os.environ.get("FRACVAL_RUN_GUI_TESTS") == "1" else ["test_qt_gui.py"]


@pytest.fixture(scope="session")
def build_tool():
    """Import tools/build.py under a private module name (avoids the PyPI 'build' package)."""
    path = ROOT / "tools" / "build.py"
    if not path.is_file():
        pytest.skip("tools/build.py not present")
    spec = importlib.util.spec_from_file_location("fracval_build_tool", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
```

- [ ] **Step 3: Write the failing tests `tests/python/test_toolchain.py`**

```python
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
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_toolchain.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'fracval._toolchain'`.

- [ ] **Step 5: Write `python/fracval/_toolchain.py`**

```python
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
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_toolchain.py -v`
Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml python/fracval/_toolchain.py tests/python/conftest.py tests/python/test_toolchain.py
git commit -m "Add stdlib compiler discovery module and pytest configuration"
```

---

### Task 3: Compiler report in `fracval-info`

**Files:**
- Modify: `python/fracval/diagnostics.py`
- Create: `tests/python/test_diagnostics.py`

**Interfaces:**
- Consumes: `fracval._toolchain.discover_toolchain`, `install_hint`.
- Produces: `runtime_info()` gains keys `fortran_compiler` and `c_compiler`, each `None` or `{"path": str, "version": str}`.

- [ ] **Step 1: Write the failing test `tests/python/test_diagnostics.py`**

```python
from __future__ import annotations

import shutil

from fracval import diagnostics


def test_runtime_info_reports_compilers():
    info = diagnostics.runtime_info()
    for key in ("fortran_compiler", "c_compiler"):
        assert key in info
        value = info[key]
        assert value is None or set(value) == {"path", "version"}


def test_format_mentions_compilers_and_hint_when_missing(monkeypatch):
    monkeypatch.setenv("FC", "no-such-fortran-zzz")
    monkeypatch.setenv("CC", "no-such-c-zzz")
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: None)
    text = diagnostics.format_runtime_info()
    assert "Fortran compiler" in text
    assert "C compiler" in text
    assert "not found" in text
    assert "conda install" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_diagnostics.py -v`
Expected: both FAIL (`KeyError`/assertion on missing keys and text).

- [ ] **Step 3: Update `python/fracval/diagnostics.py`**

Replace the file with:

```python
"""Runtime diagnostics for FracVAL-Qt Python integrations."""
from __future__ import annotations

import importlib.util
import platform
from pathlib import Path
import sys
from typing import Any

from ._toolchain import Compiler, discover_toolchain, install_hint
from .engine import available_backends, extension_available


def _compiler_dict(compiler: Compiler | None) -> dict[str, str] | None:
    if compiler is None:
        return None
    return {"path": str(compiler.path), "version": compiler.version}


def runtime_info() -> dict[str, Any]:
    """Return a JSON-friendly summary of the active FracVAL environment."""
    package_dir = Path(__file__).resolve().parent
    ext_spec = importlib.util.find_spec("fracval._fracval_fortran")
    toolchain = discover_toolchain()
    return {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "fracval_package": str(package_dir),
        "extension_available": extension_available(),
        "extension_path": getattr(ext_spec, "origin", None) if ext_spec else None,
        "available_backends": available_backends(),
        "fortran_compiler": _compiler_dict(toolchain.fortran),
        "c_compiler": _compiler_dict(toolchain.c),
    }


def _compiler_line(value: dict[str, str] | None) -> str:
    if value is None:
        return "not found"
    return f"{value['path']} ({value['version']})"


def format_runtime_info() -> str:
    """Return :func:`runtime_info` as readable diagnostic text."""
    info = runtime_info()
    lines = [
        "FracVAL-Qt runtime diagnostics",
        f"  Python executable   : {info['python_executable']}",
        f"  Python version      : {info['python_version']}",
        f"  Platform            : {info['platform']}",
        f"  Machine             : {info['machine']}",
        f"  Package directory   : {info['fracval_package']}",
        f"  Fortran compiler    : {_compiler_line(info['fortran_compiler'])}",
        f"  C compiler          : {_compiler_line(info['c_compiler'])}",
        f"  F2PY extension      : {'available' if info['extension_available'] else 'not built'}",
        f"  Extension path      : {info['extension_path'] or '-'}",
        f"  Available backends  : {', '.join(info['available_backends']) or 'none'}",
    ]
    if info["fortran_compiler"] is None or info["c_compiler"] is None:
        lines.append(f"  Install compilers   : {install_hint()}")
    if not info["available_backends"]:
        lines.append("  Next step           : python tools/build.py all")
    return "\n".join(lines)


def main() -> None:
    print(format_runtime_info())
```

- [ ] **Step 4: Run to verify it passes**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_diagnostics.py -v && /Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m fracval.diagnostics`
Expected: 2 passed; the printout shows the Homebrew gfortran path and clang/gcc.

- [ ] **Step 5: Commit**

```bash
git add python/fracval/diagnostics.py tests/python/test_diagnostics.py
git commit -m "Report discovered Fortran and C compilers in fracval-info"
```

---

### Task 4: `tools/build.py` platform rules (pure functions, tested)

**Files:**
- Create: `tools/build.py`
- Create: `tests/python/test_build_tool.py`

**Interfaces:**
- Consumes: `fracval._toolchain.discover_toolchain`, `install_hint`, `is_msvc`.
- Produces (module `tools/build.py`, loaded in tests through the `build_tool` fixture):
  - constants `CORE_SOURCES`, `EXE_SOURCES`, `EXT_SOURCES` (tuples of `.f90` names), `RUNTIME_DLLS`, `DEBUG_FFLAGS`, `IS_WINDOWS`, `IS_MACOS`
  - `executable_path() -> Path`, `extension_path() -> Path`
  - `fortran_flags(base: str, *, shared: bool) -> list[str]`
  - `c_flags(includes: list[str], *, bits: int = ...) -> list[str]`
  - `executable_link_flags() -> list[str]`, `extension_link_flags() -> list[str]`
  - `python_import_library() -> Path | None`
  - `verification_env(exclude_dirs: list[Path]) -> dict[str, str]`
  - `main(argv: list[str] | None = None) -> int` (subcommands filled in by Task 5)

- [ ] **Step 1: Write the failing tests `tests/python/test_build_tool.py`**

```python
from __future__ import annotations

import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def _force_platform(monkeypatch, build_tool, *, windows: bool, macos: bool) -> None:
    monkeypatch.setattr(build_tool, "IS_WINDOWS", windows)
    monkeypatch.setattr(build_tool, "IS_MACOS", macos)


def test_source_lists_have_fixed_order(build_tool):
    assert build_tool.CORE_SOURCES == (
        "Ctes.f90", "random.f90", "RAND_SAMPLE.f90", "a_Random_PP.f90",
        "PCA_cca.f90", "PCA_Subclusters_module.f90", "Save_results_CC.f90", "CCA_module.f90",
    )
    assert build_tool.EXE_SOURCES == build_tool.CORE_SOURCES + ("Frac_VAL_CCA.f90",)
    assert build_tool.EXT_SOURCES == build_tool.CORE_SOURCES + ("fracval_python_api.f90",)
    for name in build_tool.EXE_SOURCES + build_tool.EXT_SOURCES:
        assert (ROOT / "src" / name).is_file(), name


def test_makefile_object_list_matches_build_tool(build_tool):
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    block = makefile.split("OBJECTS :=", 1)[1].split("\n\n", 1)[0]
    objects = re.findall(r"\$\(BUILD_DIR\)/(\w+)\.o", block)
    assert objects == [Path(s).stem for s in build_tool.EXE_SOURCES]


def test_windows_rules(build_tool, monkeypatch):
    _force_platform(monkeypatch, build_tool, windows=True, macos=False)
    assert build_tool.executable_path().name == "fracval.exe"
    assert "-fPIC" not in build_tool.fortran_flags("-O2", shared=True)
    assert build_tool.fortran_flags("-O2 -g", shared=False) == ["-O2", "-g"]
    cflags = build_tool.c_flags(["/inc"], bits=64)
    assert "-DMS_WIN64" in cflags and "-fPIC" not in cflags and "-I/inc" in cflags
    assert "-DMS_WIN64" not in build_tool.c_flags([], bits=32)
    assert build_tool.executable_link_flags() == ["-static"]
    link = build_tool.extension_link_flags()
    assert link[0] == "-shared"
    assert {"-static-libgfortran", "-static-libgcc", "-static-libquadmath"} <= set(link)


def test_macos_rules(build_tool, monkeypatch):
    _force_platform(monkeypatch, build_tool, windows=False, macos=True)
    assert build_tool.executable_path().name == "fracval"
    assert "-fPIC" in build_tool.fortran_flags("-O2", shared=True)
    assert "-fPIC" not in build_tool.fortran_flags("-O2", shared=False)
    assert build_tool.extension_link_flags() == ["-bundle", "-undefined", "dynamic_lookup"]
    assert build_tool.executable_link_flags() == []
    assert build_tool.python_import_library() is None


def test_linux_rules(build_tool, monkeypatch):
    _force_platform(monkeypatch, build_tool, windows=False, macos=False)
    assert build_tool.extension_link_flags() == ["-shared"]
    assert "-fPIC" in build_tool.c_flags([], bits=64)


def test_verification_env_strips_toolchain_dirs(build_tool, tmp_path, monkeypatch):
    keep = tmp_path / "keep"
    drop = tmp_path / "drop"
    keep.mkdir()
    drop.mkdir()
    monkeypatch.setenv("PATH", os.pathsep.join([str(drop), str(keep)]))
    env = build_tool.verification_env([drop])
    entries = env["PATH"].split(os.pathsep)
    assert str(keep) in entries
    assert str(drop) not in entries
    assert env["PYTHONPATH"].endswith("python")


def test_cli_rejects_unknown_command(build_tool, capsys):
    try:
        build_tool.main(["frobnicate"])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("argparse should reject unknown commands")
```

- [ ] **Step 2: Run to verify they fail**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_build_tool.py -v`
Expected: all skipped or errored with `tools/build.py not present`.

- [ ] **Step 3: Write `tools/build.py` (rules and CLI skeleton; subcommand bodies arrive in Task 5)**

```python
#!/usr/bin/env python3
"""Cross-platform build tool for the FracVAL executable and F2PY extension.

    python tools/build.py exe     # build/fracval[.exe]
    python tools/build.py ext     # python/fracval/_fracval_fortran.<EXT_SUFFIX>
    python tools/build.py all
    python tools/build.py clean

The F2PY extension is built without Meson: F2PY only generates wrapper sources,
which are compiled together with the Fortran core by gfortran and gcc/clang.
On Windows the MinGW-w64 GNU toolchain from conda-forge is required.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PKG = ROOT / "python" / "fracval"
BUILD = ROOT / "build"
EXE_OBJ = BUILD / "obj"
EXT_BUILD = BUILD / "python_ext"
EXT_GEN = EXT_BUILD / "generated"
EXT_OBJ = EXT_BUILD / "obj"
PYF = PKG / "_fracval_fortran.pyf"

if str(ROOT / "python") not in sys.path:
    sys.path.insert(0, str(ROOT / "python"))
from fracval._toolchain import Compiler, discover_toolchain, install_hint, is_msvc  # noqa: E402

# Compile order matters: Fortran modules must be compiled before their users.
# tests/python/test_build_tool.py asserts the Makefile uses the same order.
CORE_SOURCES = (
    "Ctes.f90", "random.f90", "RAND_SAMPLE.f90", "a_Random_PP.f90",
    "PCA_cca.f90", "PCA_Subclusters_module.f90", "Save_results_CC.f90", "CCA_module.f90",
)
EXE_SOURCES = CORE_SOURCES + ("Frac_VAL_CCA.f90",)
EXT_SOURCES = CORE_SOURCES + ("fracval_python_api.f90",)
RUNTIME_DLLS = ("libgfortran-5.dll", "libquadmath-0.dll", "libgcc_s_seh-1.dll", "libwinpthread-1.dll")
DEBUG_FFLAGS = "-O0 -g -Wall -Wextra -fcheck=all -fbacktrace"

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"


# ---------- platform rules ----------

def executable_path() -> Path:
    return BUILD / ("fracval.exe" if IS_WINDOWS else "fracval")


def extension_path() -> Path:
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or (".pyd" if IS_WINDOWS else ".so")
    return PKG / ("_fracval_fortran" + suffix)


def fortran_flags(base: str, *, shared: bool) -> list[str]:
    flags = shlex.split(base)
    if shared and not IS_WINDOWS:
        flags.append("-fPIC")
    return flags


def c_flags(includes: list[str], *, bits: int = struct.calcsize("P") * 8) -> list[str]:
    flags = ["-O2"]
    if not IS_WINDOWS:
        flags.append("-fPIC")
    if IS_WINDOWS and bits == 64:
        flags.append("-DMS_WIN64")
    flags.extend(f"-I{path}" for path in includes)
    return flags


def executable_link_flags() -> list[str]:
    return ["-static"] if IS_WINDOWS else []


def extension_link_flags() -> list[str]:
    if IS_MACOS:
        return ["-bundle", "-undefined", "dynamic_lookup"]
    if IS_WINDOWS:
        return ["-shared", "-static-libgfortran", "-static-libgcc", "-static-libquadmath"]
    return ["-shared"]


def python_import_library() -> Path | None:
    """CPython import library needed when MinGW links the extension on Windows."""
    if not IS_WINDOWS:
        return None
    tag = f"{sys.version_info.major}{sys.version_info.minor}"
    lib = Path(sys.base_prefix) / "libs" / f"python{tag}.lib"
    if not lib.is_file():
        raise SystemExit(f"Python import library not found: {lib}")
    return lib


def verification_env(exclude_dirs: list[Path]) -> dict[str, str]:
    """Environment for the post-link import check: PATH without the compiler dirs."""
    excluded = {d.resolve() for d in exclude_dirs}
    env = dict(os.environ)
    entries = []
    for entry in env.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        try:
            if Path(entry).resolve() in excluded:
                continue
        except OSError:
            pass
        entries.append(entry)
    env["PATH"] = os.pathsep.join(entries)
    env["PYTHONPATH"] = str(ROOT / "python")
    return env


# ---------- helpers ----------

def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(shlex.quote(str(x)) for x in cmd), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=str(cwd or ROOT), check=True)


def require(toolchain, kind: str) -> Compiler:
    compiler = getattr(toolchain, kind)
    if compiler is None:
        raise SystemExit(
            f"No {kind.upper() if kind == 'c' else 'Fortran'} compiler found. Searched:\n  "
            + "\n  ".join(toolchain.searched)
            + f"\nInstall one with:\n  {install_hint()}"
        )
    if kind == "c" and IS_WINDOWS and is_msvc(compiler):
        raise SystemExit(
            "MSVC cl.exe cannot be combined with gfortran for the FracVAL extension.\n"
            "Install the MinGW-w64 GNU toolchain instead:\n  " + install_hint()
        )
    return compiler


# ---------- subcommands (bodies added in Task 5) ----------

def build_executable(fc: Path, fflags: str) -> Path:
    raise NotImplementedError


def build_extension(fc: Path, cc: Path, fflags: str) -> Path:
    raise NotImplementedError


def clean() -> None:
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("exe", "ext", "all", "clean"))
    parser.add_argument("--fc", help="Fortran compiler (default: $FC, then gfortran on PATH)")
    parser.add_argument("--cc", help="C compiler (default: $CC, then gcc/clang on PATH)")
    parser.add_argument("--fflags", default=os.environ.get("FFLAGS", "-O2"),
                        help="Fortran optimisation/warning flags (default: $FFLAGS or -O2)")
    parser.add_argument("--debug", action="store_true", help=f"use '{DEBUG_FFLAGS}'")
    args = parser.parse_args(argv)

    if args.command == "clean":
        clean()
        return 0

    fflags = DEBUG_FFLAGS if args.debug else args.fflags
    toolchain = discover_toolchain(fc=args.fc, cc=args.cc)
    fc = require(toolchain, "fortran")
    print(f"Fortran compiler: {fc.path} ({fc.version})")
    if args.command in ("exe", "all"):
        build_executable(fc.path, fflags)
    if args.command in ("ext", "all"):
        cc = require(toolchain, "c")
        print(f"C compiler      : {cc.path} ({cc.version})")
        build_extension(fc.path, cc.path, fflags)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify they pass**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_build_tool.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/build.py tests/python/test_build_tool.py
git commit -m "Add tools/build.py platform rules with tests"
```

---

### Task 5: `tools/build.py` subcommands, post-link import check, shim

**Files:**
- Modify: `tools/build.py` (replace the three `NotImplementedError` bodies)
- Rewrite: `python/build_fortran_extension.py`
- Modify: `tests/python/test_build_tool.py` (add DLL-copy and locked-file tests)

**Interfaces:**
- Produces: `compile_fortran(fc, flags, sources, objdir) -> list[Path]`, `verify_extension_import(exclude_dirs) -> tuple[bool, str]`, `copy_runtime_dlls(compiler_dir: Path, dest: Path) -> list[Path]`, `remove_existing_extension(target: Path) -> None`.

- [ ] **Step 1: Add failing tests to `tests/python/test_build_tool.py`**

Append:

```python
def test_copy_runtime_dlls_copies_only_present_files(build_tool, tmp_path):
    src = tmp_path / "bin"
    dest = tmp_path / "pkg"
    src.mkdir()
    dest.mkdir()
    (src / "libgfortran-5.dll").write_bytes(b"x")
    (src / "libquadmath-0.dll").write_bytes(b"y")
    copied = build_tool.copy_runtime_dlls(src, dest)
    assert sorted(p.name for p in copied) == ["libgfortran-5.dll", "libquadmath-0.dll"]
    assert (dest / "libgfortran-5.dll").read_bytes() == b"x"


def test_remove_existing_extension_reports_locked_file(build_tool, tmp_path, monkeypatch):
    target = tmp_path / "_fracval_fortran.pyd"
    target.write_bytes(b"z")

    def locked(self, missing_ok=False):
        raise PermissionError("in use")

    monkeypatch.setattr(Path, "unlink", locked)
    try:
        build_tool.remove_existing_extension(target)
    except SystemExit as exc:
        assert "Close running" in str(exc)
    else:
        raise AssertionError("locked extension should produce a SystemExit with guidance")
```

- [ ] **Step 2: Run to verify they fail**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_build_tool.py -v -k "runtime_dlls or locked"`
Expected: 2 failed with `AttributeError` (functions missing).

- [ ] **Step 3: Replace the subcommand section of `tools/build.py`**

Replace everything from `# ---------- subcommands (bodies added in Task 5) ----------` up to (not including) `def main(` with:

```python
# ---------- build steps ----------

def compile_fortran(fc: Path, flags: list[str], sources: tuple[str, ...], objdir: Path) -> list[Path]:
    objdir.mkdir(parents=True, exist_ok=True)
    objects: list[Path] = []
    for name in sources:
        obj = objdir / (Path(name).stem + ".o")
        run([fc, *flags, f"-J{objdir}", f"-I{objdir}", "-c", SRC / name, "-o", obj])
        objects.append(obj)
    return objects


def build_executable(fc: Path, fflags: str) -> Path:
    flags = fortran_flags(fflags, shared=False)
    objects = compile_fortran(fc, flags, EXE_SOURCES, EXE_OBJ)
    target = executable_path()
    run([fc, *flags, *objects, *executable_link_flags(), "-o", target])
    print(f"Built: {target.relative_to(ROOT)}")
    return target


def remove_existing_extension(target: Path) -> None:
    try:
        target.unlink(missing_ok=True)
        for dll in target.parent.glob("*.dll"):
            dll.unlink()
    except PermissionError as exc:
        raise SystemExit(
            f"Cannot replace {target.name}: the file is in use. Close running FracVAL/Python "
            "processes that have the extension loaded (GUI, notebooks) and retry."
        ) from exc


def copy_runtime_dlls(compiler_dir: Path, dest: Path) -> list[Path]:
    """Copy the gfortran runtime DLLs next to the extension (Windows fallback)."""
    copied: list[Path] = []
    for name in RUNTIME_DLLS:
        source = compiler_dir / name
        if source.is_file():
            shutil.copy2(source, dest / name)
            copied.append(dest / name)
    return copied


def verify_extension_import(exclude_dirs: list[Path]) -> tuple[bool, str]:
    """Import the built extension in a clean subprocess; return (ok, output)."""
    code = "import fracval._fracval_fortran as m; print(m.__file__)"
    proc = subprocess.run(
        [sys.executable, "-c", code], env=verification_env(exclude_dirs),
        cwd=str(BUILD), capture_output=True, text=True, check=False,
    )
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def build_extension(fc: Path, cc: Path, fflags: str) -> Path:
    import numpy as np  # deferred so `exe` works in environments without NumPy

    shutil.rmtree(EXT_BUILD, ignore_errors=True)
    EXT_GEN.mkdir(parents=True)
    EXT_OBJ.mkdir(parents=True)

    run([sys.executable, "-m", "numpy.f2py", PYF, "--build-dir", EXT_GEN])

    flags = fortran_flags(fflags, shared=True)
    objects = compile_fortran(fc, flags, EXT_SOURCES, EXT_OBJ)
    wrapper = EXT_GEN / "_fracval_fortran-f2pywrappers.f"
    wrapper_obj = EXT_OBJ / "f2pywrappers.o"
    run([fc, *flags, "-c", wrapper, "-o", wrapper_obj])
    objects.append(wrapper_obj)

    f2py_src = Path(np.f2py.__file__).resolve().parent / "src"
    includes = [sysconfig.get_paths()["include"], np.get_include(), str(f2py_src)]
    cflags = c_flags(includes)
    module_obj = EXT_OBJ / "module.o"
    fobject_obj = EXT_OBJ / "fortranobject.o"
    run([cc, *cflags, "-c", EXT_GEN / "_fracval_fortranmodule.c", "-o", module_obj])
    run([cc, *cflags, "-c", f2py_src / "fortranobject.c", "-o", fobject_obj])
    objects.extend([module_obj, fobject_obj])

    target = extension_path()
    remove_existing_extension(target)
    link = [fc, *extension_link_flags(), *objects]
    import_library = python_import_library()
    if import_library is not None:
        link.append(import_library)
    link.extend(["-o", target])
    run(link)

    exclude = [fc.parent, cc.parent]
    ok, output = verify_extension_import(exclude)
    if not ok and IS_WINDOWS:
        copied = copy_runtime_dlls(fc.parent, target.parent)
        print("Import check failed; copied runtime DLLs beside the extension: "
              + (", ".join(p.name for p in copied) or "none found"))
        ok, output = verify_extension_import(exclude)
    if not ok:
        raise SystemExit("The extension was linked but cannot be imported:\n" + output)
    print(f"Built: {target.relative_to(ROOT)}")
    return target


def clean() -> None:
    for directory in (EXE_OBJ, EXT_BUILD, BUILD / "setuptools", BUILD / "lib"):
        shutil.rmtree(directory, ignore_errors=True)
    for bdist in BUILD.glob("bdist.*"):
        shutil.rmtree(bdist, ignore_errors=True)
    for pattern in ("*.o", "*.mod", "*.png", "*.html", "fracval", "fracval.exe"):
        for path in BUILD.glob(pattern):
            if path.is_file():
                path.unlink()
    for pattern in ("_fracval_fortran*.so", "_fracval_fortran*.dylib", "_fracval_fortran*.pyd", "*.dll"):
        for path in PKG.glob(pattern):
            path.unlink()
    (BUILD / ".gitkeep").touch()
    print("Cleaned native build products.")


```

- [ ] **Step 4: Rewrite `python/build_fortran_extension.py` as a shim**

```python
#!/usr/bin/env python3
"""Compatibility shim: the build logic now lives in tools/build.py.

Equivalent to `python tools/build.py ext`. Kept so older instructions and
scripts keep working.
"""
from pathlib import Path
import runpy
import sys

sys.argv = [sys.argv[0], "ext", *sys.argv[1:]]
runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools" / "build.py"), run_name="__main__")
```

- [ ] **Step 5: Run the unit tests**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_build_tool.py -v`
Expected: 9 passed.

- [ ] **Step 6: Build everything with the new tool on macOS**

Run:
```bash
PYTHON=/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python
$PYTHON tools/build.py clean
$PYTHON tools/build.py all
$PYTHON python/build_fortran_extension.py
$PYTHON -m fracval.diagnostics
$PYTHON tests/python/test_python_api.py
```
Expected: `Built: build/fracval`, `Built: python/fracval/_fracval_fortran.cpython-313-darwin.so` (twice, once via the shim), diagnostics list both backends, the API test prints only `PASS` lines. `build/obj/` now holds the executable's objects; `build/*.o` from the Makefile are gone after `clean`.

- [ ] **Step 7: Confirm the Makefile still builds independently**

Run: `make && ls -la build/fracval`
Expected: Makefile compiles into `build/*.o` and relinks `build/fracval` without touching `build/obj/`.

- [ ] **Step 8: Commit**

```bash
git add tools/build.py python/build_fortran_extension.py tests/python/test_build_tool.py
git commit -m "Implement exe/ext/clean subcommands in tools/build.py with a post-link import check"
```

---

### Task 6: Fortran mkdir path normalisation and engine Windows fixes

**Files:**
- Modify: `src/Ctes.f90` (subroutine `ensure_output_directory` only)
- Modify: `python/fracval/engine.py:182-213`
- Create: `tests/python/test_engine_executable.py`

**Interfaces:**
- Produces: `fracval.engine._subprocess_kwargs() -> dict[str, int]` (empty on POSIX; `{"creationflags": CREATE_NO_WINDOW}` on Windows).

- [ ] **Step 1: Write the failing tests `tests/python/test_engine_executable.py`**

```python
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from fracval import FracVALConfig, GenerationError, engine


def test_subprocess_kwargs_hide_console_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    kwargs = engine._subprocess_kwargs()
    assert kwargs == {"creationflags": 0x08000000}


def test_subprocess_kwargs_empty_on_posix(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert engine._subprocess_kwargs() == {}


def test_executable_backend_creates_output_dir_before_running(tmp_path, monkeypatch):
    fake_exe = tmp_path / "fracval"
    fake_exe.write_text("")
    fake_exe.chmod(0o755)
    seen: dict[str, bool] = {}

    def fake_run(cmd, **kwargs):
        namelist = Path(cmd[1]).read_text(encoding="utf-8")
        out_dir = namelist.split("output_dir")[1].split("'")[1]
        seen["exists"] = Path(out_dir).is_dir()
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="simulated failure")

    monkeypatch.setattr(engine.subprocess, "run", fake_run)
    with pytest.raises(GenerationError):
        engine.generate(FracVALConfig(n=10, seed=1), backend="executable", executable=fake_exe)
    assert seen["exists"] is True
```

- [ ] **Step 2: Run to verify they fail**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_engine_executable.py -v`
Expected: 2 fail with `AttributeError: _subprocess_kwargs`; the third fails on `seen["exists"] is True`.

- [ ] **Step 3: Update `python/fracval/engine.py`**

Add `import sys` to the imports. Add this function after `_namelist`:

```python
def _subprocess_kwargs() -> dict[str, int]:
    """Extra subprocess options: hide the console window of the executable on Windows."""
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    return {}
```

In `_generate_executable`, replace

```python
        out = tmp_path / "results"
        inp = tmp_path / "fracval.in"
        inp.write_text(_namelist(cfg, out))
        try:
            completed = subprocess.run(
                [str(exe), str(inp)], text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False, timeout=300,
            )
```

with

```python
        out = tmp_path / "results"
        inp = tmp_path / "fracval.in"
        # Create the directory here so the Fortran shell-based mkdir is a no-op.
        out.mkdir(parents=True, exist_ok=True)
        inp.write_text(_namelist(cfg, out))
        try:
            completed = subprocess.run(
                [str(exe), str(inp)], text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False, timeout=300,
                **_subprocess_kwargs(),
            )
```

- [ ] **Step 4: Update `ensure_output_directory` in `src/Ctes.f90`**

Replace the subroutine with:

```fortran
    subroutine ensure_output_directory()
        character(len=1024) :: command
        character(len=256) :: native_dir
        character(len=64) :: os_name
        integer :: exitstat, cmdstat, envstat, idx

        os_name = ''
        call get_environment_variable('OS', os_name, status=envstat)

        if (envstat == 0 .and. index(os_name, 'Windows_NT') > 0) then
            ! cmd.exe treats '/' as a switch prefix, so hand it a native path.
            native_dir = output_dir
            do idx = 1, len_trim(native_dir)
                if (native_dir(idx:idx) == '/') native_dir(idx:idx) = '\'
            end do
            command = 'if not exist "'//trim(native_dir)//'" mkdir "'//trim(native_dir)//'"'
        else
            command = 'mkdir -p "'//trim(output_dir)//'"'
        end if

        call execute_command_line(trim(command), wait=.true., exitstat=exitstat, cmdstat=cmdstat)

        if (cmdstat /= 0 .or. exitstat /= 0) then
            write(*,'(A)') 'ERROR: Could not create output directory: '//trim(output_dir)
            stop 1
        end if
    end subroutine ensure_output_directory
```

- [ ] **Step 5: Run tests, rebuild both artifacts, and check geometry is unchanged**

Run:
```bash
PYTHON=/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python
$PYTHON -m pytest tests/python/test_engine_executable.py -v
$PYTHON tools/build.py all
bash tests/run_tests.sh
cmp tests/monodisperse/results/N_00000100_Agg_00000001.dat /private/tmp/claude-501/-Volumes-Mukut-Tweaks-git-repos-FracVAL-Qt/b4090149-80c7-4ac1-863c-f91792e63e32/scratchpad/baseline_mono.dat
cmp tests/overlap_statistical/results/N_00000030_Agg_00000001.dat /private/tmp/claude-501/-Volumes-Mukut-Tweaks-git-repos-FracVAL-Qt/b4090149-80c7-4ac1-863c-f91792e63e32/scratchpad/baseline_stat.dat
$PYTHON tests/python/test_python_api.py
```
Expected: 3 passed; both `cmp` commands print nothing (identical); API test all `PASS`.

- [ ] **Step 6: Commit**

```bash
git add src/Ctes.f90 python/fracval/engine.py tests/python/test_engine_executable.py
git commit -m "Windows-safe output directory creation and hidden console for the executable backend"
```

---

### Task 7: Qt runtime on Windows and viewer cleanup

**Files:**
- Modify: `python/fracval/desktop/qt_runtime.py`
- Modify: `python/fracval/desktop/viewer.py:24`
- Rewrite: `tests/python/test_qt_runtime_paths.py`

**Interfaces:**
- Produces: `fracval.desktop.qt_runtime.desktop_platform() -> str | None` returning `"cocoa"` on macOS, `"windows"` on Windows, `None` elsewhere. `configure_qt_runtime(headless=False)` sets `QT_QPA_PLATFORM` to that value when the plugin exists.

- [ ] **Step 1: Rewrite `tests/python/test_qt_runtime_paths.py` as pytest tests (failing ones included)**

```python
from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

from fracval.desktop import qt_runtime
from fracval.desktop.qt_runtime import (
    QtRuntimeInfo,
    _available_platforms,
    _candidate_pyside_dirs,
    _find_plugin_root,
    _platform_name,
)


def _make_layout(root: Path, plugin_subdir: str, names: tuple[str, ...]) -> Path:
    platforms = root / "PySide6" / plugin_subdir / "platforms"
    platforms.mkdir(parents=True)
    for name in names:
        (platforms / name).touch()
    return platforms


def test_macos_wheel_layout(tmp_path):
    platforms = _make_layout(tmp_path, "Qt/plugins", ("libqcocoa.dylib", "libqoffscreen.dylib", "libqminimal.dylib"))
    assert _find_plugin_root(tmp_path / "PySide6") == (tmp_path / "PySide6" / "Qt" / "plugins").resolve()
    assert _available_platforms(platforms) == ("cocoa", "minimal", "offscreen")


def test_windows_wheel_layout(tmp_path):
    platforms = _make_layout(tmp_path, "plugins", ("qwindows.dll", "qoffscreen.dll", "qminimal.dll"))
    assert _find_plugin_root(tmp_path / "PySide6") == (tmp_path / "PySide6" / "plugins").resolve()
    assert _available_platforms(platforms) == ("minimal", "offscreen", "windows")


def test_platform_names_across_os():
    assert _platform_name(Path("libqxcb.so")) == "xcb"
    assert _platform_name(Path("libqwayland.so")) == "wayland"
    assert _platform_name(Path("qwindows.dll")) == "windows"
    assert _platform_name(Path("libqcocoa.dylib")) == "cocoa"
    assert _platform_name(Path("qoffscreen.dll")) == "offscreen"


def test_windows_site_packages_fallback_is_searched(monkeypatch):
    monkeypatch.setattr(sys, "prefix", r"C:\envs\fracval")
    monkeypatch.setattr(sys, "base_prefix", r"C:\envs\fracval")
    candidates = [str(p) for p in _candidate_pyside_dirs()]
    assert any(c.endswith(os.path.join("Lib", "site-packages", "PySide6")) for c in candidates)


def test_desktop_platform_per_os(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert qt_runtime.desktop_platform() == "cocoa"
    monkeypatch.setattr(sys, "platform", "win32")
    assert qt_runtime.desktop_platform() == "windows"
    monkeypatch.setattr(sys, "platform", "linux")
    assert qt_runtime.desktop_platform() is None


@pytest.fixture
def isolated_environ(monkeypatch):
    """Give configure_qt_runtime a throwaway copy of os.environ."""
    monkeypatch.setattr(os, "environ", dict(os.environ))
    return os.environ


def _fake_info(tmp_path: Path, platforms: tuple[str, ...]) -> QtRuntimeInfo:
    return QtRuntimeInfo(
        pyside_dir=tmp_path, plugin_root=tmp_path / "plugins",
        platform_dir=tmp_path / "plugins" / "platforms", platforms=platforms,
    )


def test_configure_pins_windows_platform(tmp_path, monkeypatch, isolated_environ):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")  # e.g. inherited from CI or WSL
    monkeypatch.setattr(qt_runtime, "discover_qt_runtime", lambda: _fake_info(tmp_path, ("minimal", "offscreen", "windows")))
    info = qt_runtime.configure_qt_runtime(headless=False)
    assert info.selected_platform == "windows"
    assert os.environ["QT_QPA_PLATFORM"] == "windows"
    assert os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] == str(tmp_path / "plugins" / "platforms")


def test_configure_leaves_linux_platform_alone(tmp_path, monkeypatch, isolated_environ):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.setattr(qt_runtime, "discover_qt_runtime", lambda: _fake_info(tmp_path, ("xcb", "offscreen")))
    info = qt_runtime.configure_qt_runtime(headless=False)
    assert info.selected_platform is None
    assert "QT_QPA_PLATFORM" not in os.environ


def test_headless_prefers_offscreen(tmp_path, monkeypatch, isolated_environ):
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.setattr(qt_runtime, "discover_qt_runtime", lambda: _fake_info(tmp_path, ("windows", "minimal", "offscreen")))
    info = qt_runtime.configure_qt_runtime(headless=True)
    assert info.selected_platform == "offscreen"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
```

- [ ] **Step 2: Run to verify the new cases fail**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_qt_runtime_paths.py -v`
Expected: `test_windows_site_packages_fallback_is_searched`, `test_desktop_platform_per_os`, and `test_configure_pins_windows_platform` fail; the rest pass.

- [ ] **Step 3: Update `python/fracval/desktop/qt_runtime.py`**

In `_candidate_pyside_dirs`, replace the final loop with:

```python
    # These fallbacks help editable/Conda installs whose import metadata is
    # unusual, while still preferring the package selected by this Python.
    for base in (Path(sys.prefix), Path(sys.base_prefix)):
        yield base / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "PySide6"
        yield base / "Lib" / "site-packages" / "PySide6"  # Windows layout
```

Add after `_prefix_plugin_roots`:

```python
def desktop_platform() -> str | None:
    """QPA platform plugin FracVAL pins for a visible desktop session on this OS."""
    if sys.platform == "darwin":
        return "cocoa"
    if sys.platform == "win32":
        return "windows"
    return None
```

In `configure_qt_runtime`, replace the `elif sys.platform == "darwin" and "cocoa" in info.platforms:` branch with:

```python
    else:
        # A desktop launch pins the native platform plugin. This also neutralizes
        # an inherited offscreen/xcb value from Conda, CI, WSL, or a previous
        # shell configuration. Linux is left to Qt's own xcb/wayland selection.
        pinned = desktop_platform()
        if pinned is not None and pinned in info.platforms:
            os.environ["QT_QPA_PLATFORM"] = pinned
            selected = pinned
```

In `main()`, replace `expected = "cocoa" if sys.platform == "darwin" else None` with `expected = desktop_platform()` and the warning text with:

```python
        print(
            f"\nWARNING: expected desktop platform plugin '{expected}' was not found.",
            file=sys.stderr,
        )
```

Update the module docstring's second paragraph to read: "Some macOS and Windows Python environments (notably Conda/venv combinations or shells carrying Qt environment variables) can leave Qt with an empty or incompatible plugin search path."

- [ ] **Step 4: Update `python/fracval/desktop/viewer.py`**

Replace `self._tmp = tempfile.TemporaryDirectory(prefix="fracval-viewer-")` with:

```python
        # Chromium may still hold the HTML file when Qt tears the widget down on
        # Windows; never let that turn into an exception at exit.
        self._tmp = tempfile.TemporaryDirectory(prefix="fracval-viewer-", ignore_cleanup_errors=True)
```

- [ ] **Step 5: Run the tests, the runtime check, and the GUI smoke test**

Run:
```bash
PYTHON=/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python
$PYTHON -m pytest tests/python/test_qt_runtime_paths.py -v
$PYTHON -m fracval.desktop.qt_runtime
make gui-test PYTHON=$PYTHON
```
Expected: 8 passed; `Qt runtime check passed.` with `Selected QPA platform : cocoa`; GUI smoke test prints `PASS: native Qt GUI constructs successfully (platform=offscreen, ...)`.

- [ ] **Step 6: Commit**

```bash
git add python/fracval/desktop/qt_runtime.py python/fracval/desktop/viewer.py tests/python/test_qt_runtime_paths.py
git commit -m "Pin the Windows QPA platform, search Lib/site-packages, and tolerate viewer temp cleanup errors"
```

---

### Task 8: pytest as the single test entry point

**Files:**
- Create: `tests/python/test_fortran_cli.py`
- Delete: `tests/run_tests.sh`
- Modify: `tests/python/test_python_api.py`, `tests/python/test_visualization.py`, `tests/python/test_qt_gui.py`
- Modify: `Makefile` (test targets)

**Interfaces:**
- Consumes: `fracval.engine._find_executable(executable, required=False)`.

- [ ] **Step 1: Write `tests/python/test_fortran_cli.py`**

```python
"""Standalone-executable smoke tests (port of the former tests/run_tests.sh).

Each case runs build/fracval[.exe] on a committed namelist with the repository
root as working directory, because the namelists use relative output_dir
values, then checks the .dat and .contacts.csv outputs with NumPy.
"""
from __future__ import annotations

from pathlib import Path
import subprocess

import numpy as np
import pytest

from fracval.engine import _find_executable

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def executable() -> Path:
    exe = _find_executable(None, required=False)
    if exe is None:
        pytest.skip("standalone FracVAL executable not built (run: python tools/build.py exe)")
    return exe


def _run_case(executable: Path, name: str) -> tuple[np.ndarray, np.ndarray]:
    case_dir = ROOT / "tests" / name
    result_dir = case_dir / "results"
    result_dir.mkdir(exist_ok=True)
    for old in list(result_dir.glob("*.dat")) + list(result_dir.glob("*.contacts.csv")):
        old.unlink()

    proc = subprocess.run(
        [str(executable), str(case_dir / "fracval.in")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=600, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    dats = sorted(result_dir.glob("*.dat"))
    assert len(dats) == 1, f"expected 1 aggregate file, found {len(dats)}"
    data = np.loadtxt(dats[0], ndmin=2)
    assert data.shape[1] == 4, "output must contain exactly four columns (x y z radius)"

    contacts_path = dats[0].with_name(dats[0].name[:-4] + ".contacts.csv")
    assert contacts_path.is_file(), f"contact-overlap sidecar not found: {contacts_path}"
    contacts = np.loadtxt(contacts_path, delimiter=",", skiprows=1, ndmin=2)
    return data, contacts


@pytest.mark.parametrize("name,kind", [("monodisperse", "mono"), ("polydisperse", "poly")])
def test_size_distribution_cases(executable, name, kind):
    data, contacts = _run_case(executable, name)
    assert data.shape[0] == 100
    radii = data[:, 3]
    if kind == "mono":
        assert np.ptp(radii) <= 1e-5, "monodisperse case contains varying radii"
    else:
        assert np.ptp(radii) > 1e-5, "polydisperse case did not produce varying radii"
    assert contacts.shape[0] == 99, "expected N-1 intended contacts"


def test_fixed_overlap(executable):
    data, contacts = _run_case(executable, "overlap_fixed")
    assert data.shape[0] == 30
    assert contacts.shape[0] == 29
    assert np.allclose(contacts[:, 1], 0.05, atol=1e-5), "fixed-overlap contacts are not all 5%"


def test_statistical_overlap(executable):
    data, contacts = _run_case(executable, "overlap_statistical")
    values = contacts[:, 1]
    assert data.shape[0] == 30
    assert contacts.shape[0] == 29
    assert np.all(values >= 0.0) and np.all(values <= 0.120001), "statistical overlap out of bounds"
    assert np.ptp(values) > 0.001, "statistical overlap has no variation"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
```

- [ ] **Step 2: Run the new file against the current build and compare with the Bash harness**

Run:
```bash
PYTHON=/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python
$PYTHON -m pytest tests/python/test_fortran_cli.py -v
bash tests/run_tests.sh
```
Expected: 4 passed, and the Bash harness still passes on the same binary (both agree before the shell script is deleted).

- [ ] **Step 3: Restructure `tests/python/test_python_api.py` into pytest functions**

Keep the imports, `ROOT`, `sys.path` insert, and `geometric_pair_overlaps` unchanged. Replace `def main()` and the `__main__` block with:

```python
BASE_CFG = FracVALConfig(n=50, df=1.79, kf=1.40, rp_g=15.0, rp_gstd=1.0, seed=12345, max_attempts=100)
STAT_CFG = FracVALConfig(
    n=30, seed=24680, overlap_mode="statistical",
    overlap_mean=0.05, overlap_std=0.02, overlap_max=0.12, max_attempts=500,
)


@pytest.fixture(scope="module")
def extension():
    if not extension_available():
        pytest.skip("F2PY extension not built (run: python tools/build.py ext)")


@pytest.fixture(scope="module")
def executable() -> Path:
    exe = _find_executable(None, required=False)
    if exe is None:
        pytest.skip("standalone executable not built (run: python tools/build.py exe)")
    return exe


def test_extension_reproducibility(extension):
    a = generate(BASE_CFG, backend="extension")
    b = generate(BASE_CFG, backend="extension")
    assert np.array_equal(a.data, b.data), "extension is not reproducible for a fixed seed"
    assert np.array_equal(a.contact_overlaps, b.contact_overlaps)
    assert a.n == 50 and np.all(a.radius == 15.0)
    assert a.contact_count == a.n - 1 and not np.any(a.contact_overlaps != 0.0)


def test_extension_matches_executable(extension, executable):
    a = generate(BASE_CFG, backend="extension")
    c = generate(BASE_CFG, backend="executable", executable=executable)
    assert np.allclose(a.data, c.data, rtol=2e-6, atol=2e-5), \
        f"max abs error={float(np.max(np.abs(a.data - c.data)))}"
    assert np.allclose(a.contact_overlaps, c.contact_overlaps, rtol=1e-6, atol=1e-8)


def test_polydisperse_api(extension):
    d = generate(FracVALConfig(n=50, df=1.68, kf=0.98, rp_g=15.0, rp_gstd=2.0, seed=54321), backend="extension")
    assert np.ptp(d.radius) > 1e-5


def test_fixed_overlap_geometry(extension):
    fixed_cfg = FracVALConfig(n=30, seed=24680, overlap_mode="fixed", overlap_fraction=0.05, max_attempts=500)
    fixed = generate(fixed_cfg, backend="extension")
    assert fixed.contact_count == fixed.n - 1
    assert np.allclose(fixed.contact_overlaps, 0.05, atol=2e-7)
    actual = geometric_pair_overlaps(fixed)
    physical = actual[actual > 1e-4]
    assert len(physical) == fixed.n - 1
    assert np.allclose(physical, 0.05, atol=5e-5)


def test_statistical_overlap_geometry(extension):
    stat = generate(STAT_CFG, backend="extension")
    assert stat.contact_count == stat.n - 1
    assert not np.any(stat.contact_overlaps < 0) and not np.any(stat.contact_overlaps > STAT_CFG.overlap_max)
    assert np.ptp(stat.contact_overlaps) > 1e-4
    actual = geometric_pair_overlaps(stat)
    assert np.sum(actual > 1e-4) == stat.n - 1


def test_statistical_overlap_matches_executable(extension, executable):
    stat = generate(STAT_CFG, backend="extension")
    stat_exe = generate(STAT_CFG, backend="executable", executable=executable)
    assert np.allclose(stat.data, stat_exe.data, rtol=2e-6, atol=2e-5)
    assert np.allclose(stat.contact_overlaps, stat_exe.contact_overlaps, rtol=1e-6, atol=1e-8)


def test_config_and_bundle_round_trips(extension, tmp_path):
    a = generate(BASE_CFG, backend="extension")
    cfg_path = BASE_CFG.save_json(tmp_path / "config.json")
    assert FracVALConfig.load_json(cfg_path) == BASE_CFG
    paths = save_bundle(a, tmp_path / "bundle", stem="sample")
    loaded = load_bundle(paths["json"])
    assert np.allclose(a.data, loaded.data, rtol=1e-8, atol=1e-8)
    assert np.allclose(a.contact_overlaps, loaded.contact_overlaps, rtol=1e-8, atol=1e-8)


def test_runtime_diagnostics_detect_extension(extension):
    assert "extension" in runtime_info()["available_backends"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
```

Update the import block at the top of the file to:

```python
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from fracval import FracVALConfig, generate, load_bundle, save_bundle, runtime_info  # noqa: E402
from fracval.engine import _find_executable, extension_available  # noqa: E402
```

(`os` and `tempfile` are no longer needed.)

- [ ] **Step 4: Restructure `tests/python/test_visualization.py`**

Replace `def main()` and the `__main__` block with:

```python
@pytest.fixture(scope="module")
def aggregate():
    if not extension_available():
        pytest.skip("F2PY extension not built (run: python tools/build.py ext)")
    return generate(FracVALConfig(n=25, seed=24680), backend="extension")


def test_sphere_appearance_controls(aggregate):
    appearance = ViewerAppearance(
        particle_color="#CC5500", opacity=0.72, shininess=0.80,
        background_color="#F5F5F5", show_axes=False, show_title=False,
    )
    fig = plot_3d(aggregate, mode="spheres", sphere_resolution=7, appearance=appearance)
    assert fig.data, "Plotly figure contains no traces"
    mesh = fig.data[0]
    assert mesh.color == "#CC5500" and abs(mesh.opacity - 0.72) <= 1e-12
    assert abs(mesh.lighting.specular - 1.60) <= 1e-12
    assert fig.layout.scene.xaxis.visible is False
    assert fig.layout.scene.bgcolor == "#F5F5F5"


def test_center_mode_radius_legend_and_axes(aggregate):
    radius_view = ViewerAppearance(color_mode="radius", colorscale="Plasma", show_colorbar=True, show_axes=True)
    fig = plot_3d(aggregate, mode="centers", appearance=radius_view)
    assert fig.data[0].marker.showscale is True
    assert fig.layout.scene.xaxis.visible is True


def test_interactive_html_export(aggregate, tmp_path):
    fig = plot_3d(aggregate, mode="spheres", sphere_resolution=7)
    out = tmp_path / "python_api_preview.html"
    fig.write_html(out, include_plotlyjs=True, full_html=True)
    assert out.stat().st_size > 100_000


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
```

Add `import pytest` and `from fracval.engine import extension_available` to the imports.

- [ ] **Step 5: Make `tests/python/test_qt_gui.py` a pytest test while keeping the script form**

Replace `def main()` and the `__main__` block with:

```python
def test_main_window_constructs_headless():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    cfg = window.current_config()
    assert cfg.n == 100 and cfg.rp_gstd == 1.0, "Qt parameter panel defaults are invalid"
    assert cfg.overlap_mode == "none", "contact overlap should be disabled by default"
    assert not window.overlap_fraction_spin.isEnabled() and not window.overlap_mean_spin.isEnabled()
    assert window.windowTitle() == "FracVAL-Qt Aggregate Generator"
    appearance = window.current_appearance()
    assert not appearance.show_axes, "XYZ axes should be hidden by default"
    assert appearance.color_mode == "solid" and appearance.particle_color == "#4C78A8"
    window.close()
    app.processEvents()
    print(
        "PASS: native Qt GUI constructs successfully "
        f"(platform={qt_info.selected_platform}, plugins={qt_info.platform_dir})"
    )


if __name__ == "__main__":
    test_main_window_constructs_headless()
```

- [ ] **Step 6: Delete the Bash harness and point the Makefile at pytest**

```bash
git rm tests/run_tests.sh
```

In `Makefile`, replace the `fortran-test`, `python-ext`, `python-test`, `test`, and `gui-test` targets with:

```make
fortran-test: $(TARGET)
	$(PYTHON) -m pytest tests/python/test_fortran_cli.py

python-ext:
	$(PYTHON) tools/build.py ext --fc $(FC)

python-test: $(TARGET) python-ext
	$(PYTHON) -m pytest --ignore=tests/python/test_fortran_cli.py

test: $(TARGET) python-ext
	$(PYTHON) -m pytest

gui-test:
	FRACVAL_RUN_GUI_TESTS=1 QTWEBENGINE_DISABLE_SANDBOX=1 QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox' \
		$(PYTHON) -m pytest tests/python/test_qt_gui.py -s
```

- [ ] **Step 7: Run the full suite both ways**

Run:
```bash
PYTHON=/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python
$PYTHON -m pytest
make test PYTHON=$PYTHON
make gui-test PYTHON=$PYTHON
$PYTHON tests/python/test_python_api.py
```
Expected: `pytest` reports all tests passed with `test_qt_gui.py` not collected; `make test` passes; `make gui-test` prints the PASS line; the direct script run passes too.

- [ ] **Step 8: Commit**

```bash
git add tests/python Makefile
git commit -m "Port the Fortran smoke tests to pytest and make every Python test pytest-discoverable"
```

---

### Task 9: Packaging, version 1.1.0, and Makefile delegation

**Files:**
- Modify: `pyproject.toml`
- Create: `setup.cfg`
- Modify: `python/fracval/__init__.py:34`, `CITATION.cff:8`
- Modify: `Makefile` (`clean`, `debug`, `help`, header comment)
- Create: `tests/python/test_packaging.py`

- [ ] **Step 1: Write the failing test `tests/python/test_packaging.py`**

```python
from __future__ import annotations

from pathlib import Path
import re

import fracval

ROOT = Path(__file__).resolve().parents[2]


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1)


def _citation_version() -> str:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    return re.search(r"^version:\s*(\S+)", text, re.MULTILINE).group(1)


def test_versions_agree():
    assert fracval.__version__ == "1.1.0"
    assert _pyproject_version() == fracval.__version__
    assert _citation_version() == fracval.__version__


def test_package_data_ships_built_extension():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = text.split("[tool.setuptools.package-data]", 1)[1].split("\n\n", 1)[0]
    for pattern in ("_fracval_fortran*.so", "_fracval_fortran*.pyd", "*.dll"):
        assert pattern in block


def test_setuptools_build_dir_is_separated():
    text = (ROOT / "setup.cfg").read_text(encoding="utf-8")
    assert "build_base = build/setuptools" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -m pytest tests/python/test_packaging.py -v`
Expected: 3 failed.

- [ ] **Step 3: Update `pyproject.toml`**

Change `version = "1.0.1"` to `version = "1.1.0"` and replace the package-data block with:

```toml
[tool.setuptools.package-data]
fracval = [
  "py.typed",
  "_fracval_fortran.pyf",
  "_fracval_fortran*.so",
  "_fracval_fortran*.pyd",
  "*.dll",
]
```

- [ ] **Step 4: Create `setup.cfg`**

```ini
# Keep setuptools' own build output out of the Fortran build directory.
[build]
build_base = build/setuptools
```

- [ ] **Step 5: Bump the other two version strings**

`python/fracval/__init__.py`: `__version__ = "1.1.0"`.
`CITATION.cff`: `version: 1.1.0`.

- [ ] **Step 6: Update the Makefile `clean`, `debug`, header, and `help`**

Replace the header comment with:

```make
# FracVAL build (POSIX convenience wrapper)
# The native rules below build build/fracval incrementally on macOS/Linux.
# Cross-platform steps (F2PY extension, tests, clean) delegate to
# tools/build.py and pytest, which are also the commands Windows users run
# directly:  python tools/build.py all && python -m pytest
```

Replace the `clean` target with:

```make
clean:
	$(PYTHON) tools/build.py clean
```

Replace the `debug` target with:

```make
debug:
	$(MAKE) clean
	$(MAKE) FFLAGS='-O0 -g -Wall -Wextra -fcheck=all -fbacktrace' all
	$(PYTHON) tools/build.py ext --fc $(FC) --debug
```

In `help`, change these lines:

```make
	@echo "  make python-ext   Build the Python/Fortran extension (tools/build.py ext)"
	@echo "  make fortran-test Run the standalone smoke tests with pytest"
	@echo "  make python-test  Run Python API, extension and visualization tests with pytest"
	@echo "  make test         Run the whole pytest suite (Fortran CLI + Python)"
	@echo "  make clean        Remove compiler-generated files (tools/build.py clean)"
	@echo "Windows: run 'python tools/build.py all' and 'python -m pytest' directly."
```

- [ ] **Step 7: Verify**

Run:
```bash
PYTHON=/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python
$PYTHON -m pytest tests/python/test_packaging.py -v
make clean PYTHON=$PYTHON && ls build
make PYTHON=$PYTHON && make python-ext PYTHON=$PYTHON && $PYTHON -m pytest
$PYTHON -m pip install -e '.[gui,dev]' >/dev/null && $PYTHON -c "import fracval; print(fracval.__version__)"
```
Expected: 3 passed; after `clean`, `build/` holds only `.gitkeep`, `README.md`, and `docs/` (if present); the rebuild plus `pytest` pass; the reinstall prints `1.1.0`.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml setup.cfg python/fracval/__init__.py CITATION.cff Makefile tests/python/test_packaging.py
git commit -m "Version 1.1.0: ship built extension in package-data, isolate setuptools build dir, delegate Makefile"
```

---

### Task 10: Three-OS CI

**Files:**
- Modify: `.github/workflows/ci.yml` (replace the probe job)

- [ ] **Step 1: Replace the `conda-toolchain-probe` job with `conda-matrix`**

```yaml
  conda-matrix:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-latest
            env-file: environment.yml
          - os: macos-latest
            env-file: environment.yml
          - os: windows-latest
            env-file: environment-windows.yml
    defaults:
      run:
        shell: bash -el {0}
    env:
      QTWEBENGINE_DISABLE_SANDBOX: '1'
      QTWEBENGINE_CHROMIUM_FLAGS: '--disable-gpu --no-sandbox'
      FRACVAL_RUN_GUI_TESTS: '1'
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Install Linux libraries needed by headless QtWebEngine
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y libegl1 libgl1 libxkbcommon-x11-0 libxcb-cursor0 libnss3 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2t64

      - name: Set up Miniforge environment
        uses: conda-incubator/setup-miniconda@v3
        with:
          miniforge-version: latest
          environment-file: ${{ matrix.env-file }}
          activate-environment: fracval
          auto-activate-base: false

      - name: Report toolchain
        run: |
          conda list
          gfortran --version
          gcc --version

      - name: Install FracVAL (editable) with GUI and dev extras
        run: python -m pip install -e ".[gui,dev]"

      - name: Build executable and F2PY extension
        run: python tools/build.py all

      - name: Diagnostics
        run: |
          fracval-info
          fracval-qt-check || true

      - name: Run the pytest suite (Fortran CLI + Python API + Qt paths)
        run: python -m pytest --ignore=tests/python/test_qt_gui.py

      - name: Headless Qt GUI construction smoke test
        run: python -m pytest tests/python/test_qt_gui.py -s
```

Also change the `linux-apt` job's last two steps to:

```yaml
      - name: Build standalone Fortran generator
        # Treat free-form line truncation as an error so source remains portable
        # across GNU Fortran versions (Fortran free-form limit: 132 columns).
        run: make -j2 FFLAGS='-O2 -Werror=line-truncation'

      - name: Build the F2PY extension
        run: python tools/build.py ext

      - name: Run deterministic Fortran/Python regression suite
        run: python -m pytest --ignore=tests/python/test_qt_gui.py
```

- [ ] **Step 2: Validate the YAML and commit**

Run: `/Volumes/Mukut/Tweaks/Python_ENVs/testbed/bin/python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('ok')"`
Expected: `ok`.

```bash
git add .github/workflows/ci.yml
git commit -m "CI: build and test on Ubuntu, macOS, and Windows with Miniforge"
```

- [ ] **Step 3: Verify on GitHub and iterate**

Ask the maintainer to push. For each failing platform step, fix the cause in the relevant file and commit (do not weaken assertions). Known likely iterations, in order of probability:
1. `-static-libquadmath` unknown to the conda gfortran: remove it from `extension_link_flags()` and its test assertion; the DLL-copy fallback covers quadmath.
2. `python312.lib` not found in `sys.base_prefix/libs`: print `sys.base_prefix` in the error and check `conda list python`; conda-forge Python ships `libs/`.
3. Linux QtWebEngine smoke test needs an extra shared library: add it to the apt list.
4. Windows GUI smoke test cannot start Chromium in the runner: keep the step but add `continue-on-error: true` with a comment citing the run URL, and note in `CHANGELOG.md` that the Windows GUI smoke test is maintainer-verified.
The task is complete when the `windows-latest` job is green through `Run the pytest suite` and the maintainer confirms `fracval-gui` opens on their Windows machine.

---

### Task 11: Documentation, manual, changelog

**Files:**
- Modify: `README.md`, `doc/USAGE.md`, `doc/PYTHON_GUI.md`, `doc/INTEGRATION.md`, `doc/README.md`, `CONTRIBUTING.md`, `gui/README.md`, `examples/README.md`, `tests/README.md`, `build/README.md`, `CHANGELOG.md`, `doc/FracVAL_User_Developer_Guide.tex`
- Regenerate: `doc/FracVAL_User_Developer_Guide.pdf`

- [ ] **Step 1: README install section**

Replace the section from `## First installation on macOS/Linux` through the end of `### Normal day-to-day GUI use` with:

````markdown
## Installation (all platforms, conda/Miniforge)

Requirements: [Miniforge](https://github.com/conda-forge/miniforge) (or any
conda), and `git`. The compilers come from conda-forge.

macOS / Linux:

```bash
conda env create -f environment.yml
conda activate fracval
python -m pip install -e ".[gui,dev]"
python tools/build.py all
python -m pytest
```

Windows (Miniforge Prompt or PowerShell):

```bat
conda env create -f environment-windows.yml
conda activate fracval
python -m pip install -e ".[gui,dev]"
python tools\build.py all
python -m pytest
```

`tools/build.py all` compiles the standalone executable to `build/fracval`
(`build\fracval.exe` on Windows) and the in-memory F2PY extension into
`python/fracval/`. On Windows it uses the MinGW-w64 `gfortran`/`gcc` from
conda-forge, links the GNU runtime statically, and verifies the extension
imports before reporting success. MSVC is not supported for the extension.

Then launch the desktop application:

```bash
fracval-gui
```

### Without conda (macOS/Linux)

A plain virtual environment works when `gfortran`, a C compiler, and GNU Make
are installed from the OS (Homebrew `gcc`, or `apt install gfortran gcc make`):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[gui,dev]"
make
make python-ext PYTHON=python
make test PYTHON=python
```

The Makefile is a POSIX convenience wrapper around the same Python tooling;
Windows users call `python tools\build.py` and `python -m pytest` directly.

### Windows notes

- Use the *Miniforge Prompt* (or a shell where `conda activate fracval` works)
  so the MinGW toolchain from `gfortran_win-64` is on `PATH`.
- `fracval-info` shows which `gfortran` and `gcc` were found. If it prints
  `not found`, run `conda install -c conda-forge gfortran_win-64 gcc_win-64`.
- WSL2 with the Linux instructions remains a fully supported alternative.

### Normal day-to-day GUI use

After the first build you do **not** recompile for parameter changes:

```bash
conda activate fracval
fracval-gui
```

Rebuild with `python tools/build.py all` only after changing Fortran source or
switching Python environments.
````

Also in README: remove the `GITHUB_SETUP.md` bullet under "Repository metadata"; add `├── tools/                cross-platform build script (tools/build.py)` to the project layout tree; and replace the "Common Make targets" block with:

```text
python tools/build.py all    build executable + F2PY extension (all platforms)
python tools/build.py exe    build only the standalone executable
python tools/build.py ext    build only the F2PY extension
python tools/build.py clean  remove native build products
python -m pytest             run Fortran CLI, Python API, visualization, Qt-path tests
fracval-info                 show Python/compiler/backend diagnostics
fracval-qt-check             inspect Qt platform plugins
make / make test / make gui  POSIX shortcuts for the commands above
make docs                    compile the LaTeX manual
```

- [ ] **Step 2: `doc/USAGE.md`**

In section 2 replace the paragraph starting "The supplied Makefile and test script are designed for Linux, macOS, WSL" with:

```markdown
On every platform the recommended build command is `python tools/build.py exe`
inside the conda environment described in the top-level README. The Makefile
is a POSIX convenience wrapper (Linux, macOS, WSL); on Windows use
`python tools\build.py exe` and `python -m pytest`.
```

In section 3 add after the `make FC=gfortran FFLAGS='-O3 -march=native'` block:

````markdown
Equivalent cross-platform commands:

```bash
python tools/build.py exe                       # release build
python tools/build.py exe --debug               # runtime checks
python tools/build.py exe --fflags "-O3 -march=native"
python tools/build.py clean
```
````

In section 5 add `build\fracval.exe fracval.in` as the Windows form after `./build/fracval`. In section 7 replace the harness description with: the tests are `tests/python/test_fortran_cli.py`, run with `python -m pytest tests/python/test_fortran_cli.py` (or `make fortran-test`), and the bullet list of checks stays. Delete the two sentences about Bash 3.2. In section 9 replace `build_fortran_extension.py` with `tools/build.py` (add a `tools/` entry, keep the shim unmentioned).

- [ ] **Step 3: `doc/PYTHON_GUI.md`**

Replace section 2 ("First installation") with the conda flow from the README (both OS blocks) followed by the same three verification commands (`fracval-info`, `fracval-qt-check`, `python -m pytest`). In section 3 replace `source .venv/bin/activate` with `conda activate fracval`. In section 12 replace `make python-ext PYTHON=python` with `python tools/build.py ext` and `make` with `python tools/build.py exe`. Rename section 16 to "Common macOS/Windows Qt problems" and append:

```markdown
On Windows the expected desktop platform plugin is `windows`
(`PySide6/plugins/platforms/qwindows.dll`). `fracval-qt-check` reports it.
A leaked `QT_QPA_PLATFORM=offscreen` from a CI or WSL shell is overridden by
the launcher, and conda Qt variables (`QT_PLUGIN_PATH`) are replaced by the
PySide6 wheel's own plugin directory.
```

- [ ] **Step 4: Smaller docs**

- `doc/INTEGRATION.md` section 1: replace the venv block with `conda env create -f environment.yml` / `conda activate fracval` / `python -m pip install -e .` / `python tools/build.py ext`, and note Windows uses `environment-windows.yml`.
- `CONTRIBUTING.md`: replace the setup block with the conda flow and `python tools/build.py all`; replace `make test PYTHON=python` with `python -m pytest`; replace `make debug` with `python tools/build.py all --debug`.
- `gui/README.md`, `examples/README.md`: same substitution of the venv block.
- `tests/README.md`: replace the description of `run_tests.sh` with `tests/python/test_fortran_cli.py`, state that `python -m pytest` runs everything except the opt-in GUI smoke test, and that `FRACVAL_RUN_GUI_TESTS=1 python -m pytest tests/python/test_qt_gui.py` (or `make gui-test`) runs it.
- `build/README.md`: add "`tools/build.py` writes executable objects to `build/obj/` and extension intermediates to `build/python_ext/`; setuptools uses `build/setuptools/`."
- `doc/README.md`: no change needed beyond mentioning `environment.yml` in the provenance paragraph is unnecessary; leave as is.

- [ ] **Step 5: LaTeX manual**

In `doc/FracVAL_User_Developer_Guide.tex`:

1. Line 265: replace `build_fortran_extension.py` with `tools/build.py` in the tree listing (add a `tools/` line).
2. Replace the `\section{Requirements}` bullet "GNU Make for the supplied build commands." with "GNU Make on macOS/Linux for the optional Makefile shortcuts; Windows uses the Python build script directly."
3. Replace the whole `\section{macOS}`, `\section{Linux}`, and `\section{Windows}` blocks with:

```latex
\section{All platforms: conda/Miniforge}

The supported installation uses a conda-forge environment so the Fortran and C
compilers, NumPy, and Python match on every operating system.

macOS and Linux:
\begin{lstlisting}[language=bash]
conda env create -f environment.yml
conda activate fracval
python -m pip install -e ".[gui,dev]"
python tools/build.py all
python -m pytest
\end{lstlisting}

Windows (Miniforge Prompt):
\begin{lstlisting}[language=bash]
conda env create -f environment-windows.yml
conda activate fracval
python -m pip install -e ".[gui,dev]"
python tools\build.py all
python -m pytest
\end{lstlisting}

\code{tools/build.py all} compiles the standalone executable and the in-memory
F2PY extension. On Windows it uses the MinGW-w64 GNU toolchain provided by the
conda-forge packages \code{gfortran\_win-64} and \code{gcc\_win-64}, links the
GNU runtime libraries statically, and imports the freshly built extension in a
clean subprocess before reporting success. If that import needs the gfortran
runtime DLLs, they are copied next to the extension automatically. MSVC is not
supported for the extension because Fortran and C objects are linked by
gfortran into one module.

\begin{importantbox}
Use the same Python interpreter for installing PySide6, building the
extension, and launching the GUI. \code{fracval-info} prints the interpreter,
the discovered compilers, and the available backends.
\end{importantbox}

\section{macOS and Linux without conda}

With \code{gfortran}, a C compiler, and GNU Make from the operating system
(Homebrew \code{gcc}; \code{apt install gfortran gcc make}), a plain virtual
environment and the Makefile shortcuts work:
\begin{lstlisting}[language=bash]
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[gui,dev]"
make
make python-ext PYTHON=python
make test PYTHON=python
\end{lstlisting}

\section{Windows notes}

\begin{itemize}
  \item Run commands from the Miniforge Prompt so the MinGW toolchain is on \code{PATH}.
  \item \code{fracval-info} reports \code{not found} for a compiler when the
        environment is incomplete; fix with
        \code{conda install -c conda-forge gfortran\_win-64 gcc\_win-64}.
  \item The standalone executable is \path{build\fracval.exe}. Namelist
        \code{output\_dir} values may use forward or backward slashes.
  \item WSL2 with the Linux instructions remains supported.
\end{itemize}
```

4. In the "Installation targets" table add rows `\code{python tools/build.py all} & Build executable and extension on any platform. \\`, `\code{python tools/build.py clean} & Remove native build products. \\`, and change `make python-ext` purpose to "Rebuild only the F2PY extension (POSIX shortcut for \code{tools/build.py ext})."
5. In "Verify the installation" add after the `cocoa` sentence: "On Windows the expected plugin is \code{windows}."
6. In the "Five-Minute Workflows" GUI launch block replace `source .venv/bin/activate` with `conda activate fracval`.
7. In the Tests chapter replace the `make test` description with `python -m pytest` and state that `tests/python/test\_fortran\_cli.py` replaced the shell harness; in "Qt tests" add `FRACVAL\_RUN\_GUI\_TESTS=1 python -m pytest tests/python/test\_qt\_gui.py`.
8. In "Debug Fortran build" add `python tools/build.py all --debug`.
9. In Troubleshooting "F2PY extension build fails" replace `which gfortran` / `gfortran --version` with `fracval-info` and the rebuild block with `python tools/build.py clean` / `python tools/build.py ext`. Add a new section:

```latex
\section{Windows: \code{ImportError: DLL load failed} for the extension}

The extension is linked with a static GNU runtime and verified at build time.
If an import still fails, rebuild with \code{python tools/build.py ext} from
the activated \code{fracval} environment; the build script copies
\code{libgfortran-5.dll}, \code{libquadmath-0.dll}, \code{libgcc\_s\_seh-1.dll},
and \code{libwinpthread-1.dll} beside the extension when they are needed.
```

10. In the command tables (lines 1420-1430 and 1515-1535) add `\code{python tools/build.py}` rows and update `make test` to "Run the pytest suite".

- [ ] **Step 6: `CHANGELOG.md`**

Insert above `## 1.0.1`:

```markdown
## 1.1.0 - 2026-09-03

### Added

- Native Windows support with a conda-forge MinGW-w64 toolchain (`environment-windows.yml`).
- `tools/build.py`: one cross-platform command to build the standalone executable and the F2PY extension (`exe`, `ext`, `all`, `clean`), with a post-link import check and automatic gfortran runtime DLL fallback on Windows.
- `environment.yml` for macOS/Linux conda users.
- `fracval-info` now reports the discovered Fortran and C compilers.
- GitHub Actions matrix on Ubuntu, macOS, and Windows.

### Changed

- All tests run under `pytest`; the Bash harness `tests/run_tests.sh` was replaced by `tests/python/test_fortran_cli.py`.
- The Makefile is a POSIX convenience wrapper that delegates cross-platform steps to `tools/build.py` and `pytest`.
- The Qt launcher pins the `windows` platform plugin on Windows, mirroring `cocoa` on macOS.
- setuptools build output moved to `build/setuptools/`; built extensions are included in package-data.

### Fixed

- Output-directory creation from the Fortran executable now passes a native path to `cmd.exe`.
- The executable backend no longer flashes a console window on Windows and creates its output directory before launching.
- WebEngine viewer temp-directory cleanup cannot raise at exit on Windows.
- Removed a dead `GITHUB_SETUP.md` link from the README.
```

- [ ] **Step 7: Rebuild the manual and check for stale references**

Run:
```bash
make docs
grep -rn "run_tests.sh\|build_fortran_extension\|GITHUB_SETUP" README.md doc/*.md doc/*.tex CONTRIBUTING.md gui/README.md examples/README.md tests/README.md Makefile
```
Expected: `doc/FracVAL_User_Developer_Guide.pdf` is regenerated without LaTeX errors; grep returns no matches.

- [ ] **Step 8: Commit**

```bash
git add README.md doc CONTRIBUTING.md gui/README.md examples/README.md tests/README.md build/README.md CHANGELOG.md
git commit -m "Docs: conda-first installation for macOS, Linux, and Windows; 1.1.0 changelog"
```

---

## Completion checklist

- [ ] `python -m pytest` passes on the maintainer's macOS machine with the extension and executable built by `tools/build.py all`.
- [ ] Baseline `.dat` files from Task 0 are byte-identical to the post-change outputs (Task 6 step 5).
- [ ] The `windows-latest` CI job is green through the pytest step; the maintainer has launched `fracval-gui` on Windows.
- [ ] Spec section 9 items are resolved and recorded in the spec.
