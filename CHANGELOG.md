# FracVAL-Qt changelog

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
