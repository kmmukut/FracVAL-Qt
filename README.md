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

## First installation on macOS/Linux

Requirements: Python 3.10+, GNU Fortran (`gfortran`), GNU Make, and a C compiler.
On macOS, Homebrew's `gcc` package provides `gfortran`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
make install-gui PYTHON=python
make
make qt-check PYTHON=python
make gui-test PYTHON=python
make test PYTHON=python
```

Then launch the desktop application:

```bash
fracval-gui
```

or from the source tree:

```bash
make gui PYTHON=python
```

### Normal day-to-day GUI use

After the first installation/build, you do **not** recompile for parameter
changes:

```bash
cd /path/to/FracVAL-Qt
source .venv/bin/activate
fracval-gui
```

Rebuild only after changing Fortran source or changing Python environments.

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
├── Makefile
├── pyproject.toml
└── fracval.in             default Fortran runtime namelist
```

## Repository metadata

- [`NOTICE.md`](NOTICE.md) - original FracVAL attribution and scope of modifications
- [`CITATION.cff`](CITATION.cff) / [`CITATION.md`](CITATION.md) - citation metadata
- [`AUTHORS.md`](AUTHORS.md) - original authors and contributor policy
- [`CONTRIBUTING.md`](CONTRIBUTING.md) - development and pull-request guidance
- [`GITHUB_SETUP.md`](GITHUB_SETUP.md) - suggested repository description and first-push commands

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
make                 build standalone Fortran executable
make install         install Python package + build F2PY extension
make install-gui     install Python package + Qt dependencies + extension
make python-ext      build/rebuild the in-memory Fortran extension
make test            run scientific Fortran/Python regression tests
make qt-check        inspect Qt platform plugins
make gui-test        construct the Qt GUI in headless smoke-test mode
make gui             launch the native GUI
make docs            compile the LaTeX manual
make info            show Python/backend diagnostics
make clean           remove native build products
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
