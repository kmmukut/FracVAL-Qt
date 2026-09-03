# FracVAL-Qt changelog

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

## 1.0.1 - 2026-09-02

### Fixed

- Wrapped overlong free-form Fortran statements to stay within the standard 132-column source limit.
- Prevented strict/newer `gfortran` builds from truncating the `sticking_process` declaration and producing cascading `Unexpected ... in CONTAINS section` errors.
- CI now treats Fortran line truncation as an error so this portability regression is caught immediately.

## 1.0.0 - FracVAL-Qt repository baseline

- Consolidated FracVAL into a single cross-platform-oriented source tree.
- Moved user-changeable simulation settings from compile-time parameters to runtime inputs.
- Added out-of-tree Fortran build under `build/`.
- Added deterministic random-seed control.
- Added Python API and F2PY in-memory backend plus standalone-executable fallback.
- Added native PySide6/Qt desktop GUI and offline Plotly 3-D viewer.
- Added particle appearance controls and axis-free default visualization.
- Added fixed and bounded statistical intended-contact overlap models.
- Added contact-overlap history and overlap statistics.
- Added configuration JSON helpers, result bundle save/load helpers, and runtime diagnostics.
- Added runnable Python integration examples and parameter-sweep templates.
- Added detailed LaTeX/PDF user and developer manual plus Markdown quick references.
- Added Fortran/Python/visualization/Qt smoke and regression tests.

## Legacy basis

The numerical PCA/CCA aggregation implementation is derived from the original
FracVAL source distributed by J. Morán, A. Fuentes, F. Liu, and J. Yon. See
`NOTICE.md`, `CITATION.md`, and `LICENSE` for provenance and licensing. The
modern interface work is organized to keep that scientific core separate from
the Python and GUI layers.
