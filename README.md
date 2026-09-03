# FracVAL-Qt 1.0

**FracVAL-Qt** is a modern Python/Qt interface and maintained derivative of the
original **FracVAL** Fortran fractal aggregate generator. It preserves the
particle-cluster (PCA) and cluster-cluster (CCA) numerical core while adding
runtime configuration, a reusable Python API, a native Qt desktop GUI,
interactive 3-D visualization, reproducible random seeds, and optional intended
contact overlap.

## Origin, attribution, and license

The original FracVAL software and aggregation methodology were developed by
**J. Morán, A. Fuentes, F. Liu, and J. Yon** and published in *Computer Physics
Communications* 239 (2019), 225-237, DOI
`10.1016/j.cpc.2019.01.015`. The corresponding software release is archived at
Mendeley Data, DOI `10.17632/mgf8wdcsfb.1`.

FracVAL-Qt is a derivative work. The original authors should be credited for
the original FracVAL algorithm and Fortran implementation; the Python/Qt
interface, packaging, testing, documentation, reproducibility controls, and
overlap extensions are subsequent modifications maintained in this repository.
Nothing here implies endorsement of those later modifications by the original
authors.

The project is distributed under the **GNU General Public License version 3
(GPLv3)**. See [`LICENSE`](LICENSE), [`NOTICE.md`](NOTICE.md), and
[`CITATION.md`](CITATION.md).

## Choose an interface

| Interface | Best for | Normal command |
|---|---|---|
| Native Qt GUI | Interactive generation, visualization, export | `fracval-gui` |
| Python API | Scripts, notebooks, parameter sweeps, integration | `from fracval import generate` |
| Fortran CLI | Traditional compiled workflows and batch jobs | `./build/fracval fracval.in` |

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

## Five-line Python example

```python
from fracval import FracVALConfig, generate

cfg = FracVALConfig(n=100, df=1.79, kf=1.40, seed=12345)
agg = generate(cfg)
print(agg.data.shape, agg.radius_of_gyration)
```

The returned `Aggregate` exposes NumPy arrays `x`, `y`, `z`, `radius`, the
combined `(N,4)` array `data`, contact-overlap statistics, metadata, and export
methods.

For a polydisperse case:

```python
cfg = FracVALConfig(
    n=100, df=1.68, kf=0.98,
    rp_g=15.0, rp_gstd=2.0,
    seed=67890,
)
agg = generate(cfg)
```

For a bounded statistical intended-contact overlap model:

```python
cfg = FracVALConfig(
    n=100, seed=24680,
    overlap_mode="statistical",
    overlap_mean=0.05,
    overlap_std=0.02,
    overlap_max=0.12,
)
agg = generate(cfg)
```

## Portable Python results

```python
from fracval import save_bundle, load_bundle

paths = save_bundle(agg, "run_001", stem="aggregate_0001")
restored = load_bundle(paths["json"])
```

Configuration objects can also be saved and loaded directly:

```python
cfg.save_json("case.json")
cfg2 = FracVALConfig.load_json("case.json")
```

## Diagnostics

```bash
fracval-info
fracval-qt-check
```

`fracval-info` reports the active Python, package location, F2PY extension, and
available generation backends. `fracval-qt-check` additionally diagnoses the
Qt platform-plugin installation used by the desktop GUI.

## Project layout

```text
FracVAL-Qt/
├── src/                  Fortran PCA/CCA core and F2PY-facing wrapper
├── python/fracval/       Python API, I/O, visualization, Qt desktop app
├── gui/                  source-tree GUI launcher
├── examples/             copy-pasteable Python integration examples
├── tests/                Fortran, Python, overlap and GUI smoke tests
├── plot/                 standalone plotting script and notebooks
├── doc/                  Markdown guides + LaTeX/PDF user/developer manual
├── build/                generated compiler and documentation products
├── tools/                cross-platform build script (tools/build.py)
├── Makefile
├── pyproject.toml
└── fracval.in             default Fortran runtime namelist
```

## Repository metadata

- [`NOTICE.md`](NOTICE.md) - original FracVAL attribution and scope of modifications
- [`CITATION.cff`](CITATION.cff) / [`CITATION.md`](CITATION.md) - citation metadata
- [`AUTHORS.md`](AUTHORS.md) - original authors and contributor policy
- [`CONTRIBUTING.md`](CONTRIBUTING.md) - development and pull-request guidance

## Documentation

Start with the compiled manual:

- [`doc/FracVAL_User_Developer_Guide.pdf`](doc/FracVAL_User_Developer_Guide.pdf)
- [`doc/FracVAL_User_Developer_Guide.tex`](doc/FracVAL_User_Developer_Guide.tex)

Additional quick references:

- [`doc/README.md`](doc/README.md) - documentation index
- [`doc/USAGE.md`](doc/USAGE.md) - standalone Fortran/runtime workflow
- [`doc/PYTHON_GUI.md`](doc/PYTHON_GUI.md) - Python API and native Qt GUI
- [`doc/OVERLAP.md`](doc/OVERLAP.md) - intended-contact overlap model
- [`doc/API_REFERENCE.md`](doc/API_REFERENCE.md) - compact Python API reference
- [`doc/INTEGRATION.md`](doc/INTEGRATION.md) - embedding FracVAL in another Python project
- [`examples/README.md`](examples/README.md) - runnable examples

Rebuild the PDF manual with:

```bash
make docs
```

## Common Make targets

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

## Important model notes

- `rp_gstd = 1.0` gives monodisperse primary particles; values above 1 produce
  the lognormal polydisperse distribution used by the existing code.
- `tol_ov` remains the strict numerical tolerance for **unintended** overlap.
- `overlap_mode="fixed"` or `"statistical"` applies overlap only at the
  intended joining contact; unrelated particles remain collision protected.
- A fixed seed is intended for reproducibility within a consistent compiler,
  runtime, backend and platform. Floating-point/toolchain changes can alter the
  exact stochastic trajectory.
- The F2PY extension is the preferred Python backend. The standalone executable
  remains available as a fallback.

See the full manual for architecture, formulas, API details, GUI walkthrough,
output formats, testing, troubleshooting, and extension guidance.
