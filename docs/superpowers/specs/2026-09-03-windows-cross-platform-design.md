# FracVAL-Qt cross-platform (Windows) support design

Date: 2026-09-03
Status: approved design, pre-implementation
Target release: 1.1.0

## 1. Goal

Make FracVAL-Qt build, test, and run on Windows with the same commands and the
same conda/miniforge-based environment that macOS and Linux users get, while
leaving the Fortran numerical core untouched. Windows becomes a first-class,
CI-verified platform rather than a "use WSL" footnote.

## 2. Decisions already made

| Decision | Choice | Reason |
|---|---|---|
| Windows Fortran toolchain | MinGW-w64 gfortran + gcc from conda-forge (`gfortran_win-64`; fallback `m2w64-gcc-fortran`) | One compiler family and one flag dialect on all three OSes. flang/MSVC is out of scope. |
| Build tooling | Python-native build script; Makefile remains a POSIX convenience wrapper | Smallest change that makes Windows first-class; extends the Meson-free helper that already exists. CMake/scikit-build-core rejected for now. |
| Test tooling | pytest as the single cross-platform entry point | `pytest` is already in the `dev` extra; the Bash harness must be ported anyway. |
| Verification | GitHub Actions matrix (Ubuntu, macOS, Windows) plus the maintainer's own Windows machine | The implementation session cannot run Windows. |
| Qt/PySide6 source | pip wheel inside the conda env on every OS | The wheel bundles Qt and QtWebEngine; conda-forge PySide6 does not reliably include WebEngine. |
| Extras included | pytest port, package-data for the built extension, separate setuptools build dir, compiler discovery in `fracval-info` | Small, and each removes a real papercut found in review. |

## 3. Out of scope

- LLVM flang or MSVC toolchains.
- Windows on ARM64.
- Binary wheels, installers, or a console-free GUI launcher (`gui-scripts`).
- Any change to PCA/CCA numerics or to fixed-seed outputs.

## 4. Architecture overview

```
environment.yml ──> conda env (python, numpy, plotly, pytest, [win: gfortran_win-64])
                          │  pip install -e .[gui]   (PySide6 wheel)
                          ▼
tools/build.py  ──> build/fracval[.exe]          (standalone executable)
                ──> python/fracval/_fracval_fortran.<EXT_SUFFIX>  (+ runtime DLLs on Windows if needed)
                          │
pytest          ──> tests/python/test_fortran_cli.py   (ported run_tests.sh)
                ──> tests/python/test_python_api.py, test_visualization.py, test_qt_runtime_paths.py
                ──> tests/python/test_qt_gui.py (headless, opt-in)
```

The Makefile keeps its native incremental Fortran rules for POSIX developers and
delegates `python-ext`, `test`, and `clean` to the Python tooling so there is one
implementation of each cross-platform step.

## 5. Components

### 5.1 `environment.yml` (new, repo root)

Two conda-forge environment files, because `environment.yml` has no
platform selectors:

- `environment.yml` (macOS/Linux): `python=3.12`, `numpy>=1.24`,
  `plotly>=5.18`, `pytest>=7`, and `gfortran` from conda-forge so the compiler
  comes from the same channel on every OS. `make` is expected from the OS.
- `environment-windows.yml`: the same packages plus `gfortran_win-64` and
  `gcc_win-64` (MinGW-w64 UCRT GCC with activation scripts).

Both files carry a `pip:` section with `PySide6>=6.6` so the wheel's bundled
Qt and QtWebEngine are used. The editable install is not in the file; the docs
run `pip install -e .[gui]` explicitly after `conda activate fracval`.

### 5.2 Toolchain discovery (`tools/build.py`)

Search order for the Fortran compiler: `FC` env var, `gfortran` on PATH,
`x86_64-w64-mingw32-gfortran` on PATH, then on Windows
`%CONDA_PREFIX%\Library\mingw-w64\bin` and `%CONDA_PREFIX%\Library\bin`.
Search order for the C compiler: `CC` env var, `sysconfig` `CC` (POSIX only),
`gcc`, `x86_64-w64-mingw32-gcc`, then the same conda directories. On Windows the
C compiler must be the MinGW `gcc` matching gfortran; MSVC `cl` is rejected with
an explicit message because Fortran and C objects are linked by gfortran into one
DLL.

The discovered compilers, their versions (`--version` first line), and their
directories are exposed by a function `discover_toolchain()` so both the build
script and `fracval-info` use the same logic. That function lives in a new
small module `python/fracval/_toolchain.py` (stdlib only, importable without
NumPy) and `tools/build.py` imports it.

### 5.3 Build script (`tools/build.py`)

Replaces `python/build_fortran_extension.py`; the old path stays as a two-line
shim that calls the new script's `ext` subcommand so existing docs and muscle
memory keep working.

Subcommands:

- `exe`: compile the nine standalone Fortran sources in the existing order into
  `build/obj/` and link `build/fracval` (`build/fracval.exe` on Windows).
- `ext`: generate F2PY wrappers, compile the nine extension sources plus the
  wrapper and the two C files, link the extension into `python/fracval/`.
- `all`: `exe` then `ext`.
- `clean`: remove `build/obj/`, `build/python_ext/`, `build/setuptools/`, the
  executable, built extensions and adjacent runtime DLLs, `build/lib/`,
  `build/bdist.*`, and plot smoke-test outputs. Keep `build/.gitkeep` and
  `build/README.md`.

Options: `--fc`, `--cc`, `--fflags` (default `-O2`), `--debug` (uses
`-O0 -g -Wall -Wextra -fcheck=all -fbacktrace`), `--python` is not needed
because the script runs under the target interpreter.

Platform rules:

| Concern | POSIX | Windows |
|---|---|---|
| Executable name | `fracval` | `fracval.exe` |
| Fortran flags | `-O2 -fPIC` (ext), `-O2` (exe) | `-O2` (no `-fPIC`) |
| C defines | none | `-DMS_WIN64` (64-bit) |
| Python import library | not linked | `sys.base_prefix/libs/python<XY>.lib` passed as a link input |
| Extension link | macOS: `-bundle -undefined dynamic_lookup`; Linux: `-shared` | `-shared -static-libgfortran -static-libgcc -static-libquadmath` |
| Executable link | as today | `-static` |
| Extension suffix | `sysconfig EXT_SUFFIX` | `sysconfig EXT_SUFFIX` (`.cp312-win_amd64.pyd`) |

The source list and compile order are defined once in `tools/build.py`. The
Makefile keeps its own explicit object list for incremental POSIX builds; a
pytest test asserts the two lists match so they cannot drift.

Post-link verification (`ext` only): import the module in a subprocess whose
PATH has the compiler directory removed and whose working directory is neutral.
On Windows, if the import fails with a DLL-load error, copy
`libgfortran-5.dll`, `libquadmath-0.dll`, `libgcc_s_seh-1.dll`, and
`libwinpthread-1.dll` from the compiler's directory next to the `.pyd` and
retry once. If it still fails, exit non-zero with the captured error.

Error handling: a missing compiler prints the search list and the conda
install command for the current OS. On Windows, a `PermissionError` while
replacing the `.pyd` prints "close running FracVAL/Python processes that have
the extension loaded" instead of a traceback. All subprocess commands are echoed
before running, as today.

### 5.4 Fortran core (`src/Ctes.f90`)

`ensure_output_directory` replaces `/` with `\` in the path it hands to
cmd.exe when `OS=Windows_NT`. Nothing else in `src/` changes. The Python
executable backend also creates the output directory before launching the
executable, so the shell-out is a no-op in that path.

### 5.5 Python engine (`python/fracval/engine.py`)

- `_generate_executable` creates `out` before running and passes
  `creationflags=subprocess.CREATE_NO_WINDOW` on Windows.
- `_find_executable` already checks `fracval.exe`; unchanged.

### 5.6 Qt runtime (`python/fracval/desktop/qt_runtime.py`, `viewer.py`)

- `_candidate_pyside_dirs` adds `<prefix>/Lib/site-packages/PySide6` for
  Windows layouts.
- `configure_qt_runtime` sets `QT_QPA_PLATFORM=windows` on win32 when that
  plugin is present, mirroring the macOS `cocoa` rule, so an inherited
  `offscreen`/`xcb` value from CI or WSL cannot break the desktop launch.
- `main()` warns when the expected desktop plugin (`cocoa` on macOS,
  `windows` on Windows) is missing.
- `AggregateViewer` creates its `TemporaryDirectory` with
  `ignore_cleanup_errors=True`.

### 5.7 Diagnostics (`python/fracval/diagnostics.py`)

`runtime_info()` gains `fortran_compiler`, `c_compiler` (path and version or
`None`) from `_toolchain.discover_toolchain()`, and `format_runtime_info()`
prints them. The "next step" hint names `tools/build.py` and, when a compiler
is missing, the conda install command for the current OS.

### 5.8 Tests

- `tests/python/test_fortran_cli.py` (new) ports `tests/run_tests.sh`: for each
  of the four namelists it clears the result directory, runs the executable,
  and asserts row count, four columns, mono/poly radius behaviour, contact
  sidecar row count, fixed 5% overlap, and bounded statistical variation, using
  NumPy. It skips (not fails) when the executable is not built. It locates the
  executable through `fracval.engine._find_executable` so `FRACVAL_EXECUTABLE`
  works.
- `tests/run_tests.sh` is deleted; `make fortran-test` runs the pytest file.
- `test_python_api.py`, `test_visualization.py`, and `test_qt_runtime_paths.py`
  are restructured into `test_*` functions and keep a `__main__` block that
  calls them in order, so `python tests/python/test_x.py` still works.
- `test_qt_runtime_paths.py` adds `qwindows.dll`/`libqxcb.so` name cases and a
  Windows-layout (`PySide6/plugins/platforms`) case.
- `tests/python/test_build_manifest.py` (new) asserts the Makefile object list
  equals the `tools/build.py` source list.
- `test_qt_gui.py` stays opt-in (`make gui-test` / explicit path) because it
  needs PySide6; it is excluded from default collection via `conftest.py`
  unless `FRACVAL_RUN_GUI_TESTS=1`.
- `pytest.ini`/`[tool.pytest.ini_options]` in `pyproject.toml` sets
  `testpaths = tests/python` and `pythonpath = python`.

### 5.9 Packaging (`pyproject.toml`, `setup.cfg`)

- Package-data adds `_fracval_fortran*.so`, `_fracval_fortran*.pyd`, and
  `*.dll` so a non-editable `pip install .` after `tools/build.py ext` ships
  the extension.
- `setup.cfg` with `[build] build_base = build/setuptools` keeps setuptools out
  of the Fortran build area. `.gitignore` already covers `build/*`.
- Version bumps to 1.1.0 in `pyproject.toml`, `__init__.py`, `CITATION.cff`.

### 5.10 Makefile

Targets keep their names. `python-ext`, `python-test`, `fortran-test`, `test`,
and `clean` delegate to `tools/build.py` / `pytest`. The native `$(TARGET)`
rules stay for incremental POSIX builds. `install`/`install-gui` unchanged.
The Makefile is documented as POSIX-only; Windows users call the Python tooling
directly.

### 5.11 CI (`.github/workflows/ci.yml`)

Two jobs:

- `linux-apt` (existing): Ubuntu, Python 3.11/3.12, apt gfortran, `make` with
  `-Werror=line-truncation`, `pytest`.
- `conda-matrix`: `ubuntu-latest`, `macos-latest`, `windows-latest` via
  `conda-incubator/setup-miniconda` with `environment.yml` (Windows uses
  `environment-windows.yml`). Steps: `pip install -e .[gui,dev]`,
  `python tools/build.py all`, `fracval-info`, `pytest`, and the headless GUI
  smoke test with `QT_QPA_PLATFORM=offscreen`. Every step is a plain Python
  or pytest invocation so the same step list runs under the default shell of
  each runner without shell-specific syntax.

### 5.12 Documentation

- `README.md`: conda-based quick start per OS (three tabs of commands), the
  Windows section replacing the WSL advice, `tools/build.py` in the target
  table, dead `GITHUB_SETUP.md` link removed.
- `doc/USAGE.md`, `doc/PYTHON_GUI.md`, `doc/INTEGRATION.md`,
  `CONTRIBUTING.md`, `gui/README.md`, `examples/README.md`, `tests/README.md`:
  replace `python3 -m venv` blocks with the conda flow (venv kept as an
  alternative), replace `make` steps with the cross-platform equivalents where
  a Windows user would hit them.
- `doc/FracVAL_User_Developer_Guide.tex`: rewrite the Windows section and the
  build/test chapters; the PDF is rebuilt with `make docs` (LaTeX available
  locally).
- `CHANGELOG.md`: 1.1.0 entry.

## 6. Data flow changes

None for generation. The only new data is the toolchain description dict
returned by `discover_toolchain()`, consumed by `tools/build.py` and
`fracval-info`.

## 7. Error handling summary

| Failure | Behaviour |
|---|---|
| No Fortran/C compiler | Build script and `fracval-info` list what was searched and print the conda install command for the OS. |
| MSVC `cl` detected as CC on Windows | Rejected with an explanation; user pointed to `gcc_win-64`. |
| Extension import fails after link (Windows) | Copy runtime DLLs beside `.pyd`, retry once, then fail with the loader error. |
| `.pyd` locked | Clear message to close running processes. |
| Executable missing when tests run | Fortran CLI tests skip with a reason; API tests that compare against the executable skip that comparison. |
| Qt platform plugin missing | Existing `RuntimeError` path; `fracval-qt-check` names the expected plugin per OS. |

## 8. Testing strategy

- Every change that can run on macOS is verified locally in this session
  (`tools/build.py all`, `pytest`, `make test`, `make gui-test`).
- Windows behaviour is verified by the CI Windows job on push and by the
  maintainer on a Windows machine. The plan front-loads a toolchain probe
  commit (environment file + CI job that only installs and prints compiler
  versions) so the package names are confirmed before the build script is
  finished.
- Fixed-seed regression outputs must be unchanged on Linux and macOS; the
  Windows build is expected to reproduce them within the existing tolerances of
  `test_python_api.py`, and the CI job asserts that.

## 9. Open verification items (resolved during implementation, not design)

1. `gfortran_win-64` version pin and whether it pulls in `gcc_win-64`
   automatically or needs an explicit entry.
2. Whether `-static-libquadmath` is accepted by that GCC; if not, drop it and
   rely on the DLL-copy fallback.
3. Whether the QtWebEngine offscreen smoke test runs on `windows-latest`; if it
   cannot, the Windows CI job runs `fracval-qt-check` only and the GUI smoke
   test is marked as maintainer-machine verification.
