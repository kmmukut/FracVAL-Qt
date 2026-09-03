# FracVAL usage guide

> For the complete user/developer manual, including the Python API and Qt GUI, see `FracVAL_User_Developer_Guide.pdf`.

## 1. Overview

FracVAL reads simulation settings from a text input file at **runtime**. Build
the Fortran program once, edit an input file as often as needed, and rerun the
same executable.

The default workflow is:

```bash
make
./build/fracval fracval.in
```

Changing `N`, `Df`, `kf`, the primary-particle size distribution, the number of
aggregates, or the output directory does **not** require recompilation.
Recompile only after changing source files under `src/`.

---

## 2. Requirements

### For the generator

- GNU Fortran (`gfortran`)
- GNU Make

On Debian/Ubuntu, for example:

```bash
sudo apt install gfortran make
```

On every platform the recommended build command is `python tools/build.py exe`
inside the conda environment described in the top-level README. The Makefile
is a POSIX convenience wrapper (Linux, macOS, WSL); on Windows use
`python tools\build.py exe` and `python -m pytest`.

### For plotting

Python 3 and the packages listed in `plot/requirements.txt`:

```bash
python3 -m pip install -r plot/requirements.txt
```

---

## 3. Build

From the project root:

```bash
make
```

The compiler-generated files stay out of `src/`:

```text
build/
├── *.o
├── *.mod
└── fracval
```

A parallel build is supported:

```bash
make -j
```

Useful build targets:

```bash
make              # release build
make debug        # rebuild with warnings and runtime checks
make clean        # remove generated compiler files
make help         # list common targets
```

To use a different compiler or optimization flags:

```bash
make FC=gfortran FFLAGS='-O3 -march=native'
```

Equivalent cross-platform commands:

```bash
python tools/build.py exe                       # release build
python tools/build.py exe --debug               # runtime checks
python tools/build.py exe --fflags "-O3 -march=native"
python tools/build.py clean
```

---

## 4. Runtime input file

FracVAL uses a standard Fortran namelist. The default file is `fracval.in`:

```text
&fracval
    N                   = 100
    Df                  = 1.79
    kf                  = 1.40
    rp_g                = 15.0
    rp_gstd             = 1.00
    Quantity_aggregates = 1
    Ext_case            = 0
    Nsubcl_perc         = 0.10
    tol_ov              = 1.0e-6
    random_seed_value   = -1
    overlap_mode        = 'none'
    overlap_fraction    = 0.05
    overlap_mean        = 0.05
    overlap_std         = 0.02
    overlap_max         = 0.12
    output_dir          = 'results'
/
```

The block must start with `&fracval` and end with `/`. Text after `!` is a
comment. Namelist variable names are case-insensitive.

### Input parameters

| Parameter | Meaning | Validation / typical value |
|---|---|---|
| `N` | Primary particles per aggregate | integer, `N >= 5` |
| `Df` | Fractal dimension | positive real |
| `kf` | Fractal prefactor | positive real |
| `rp_g` | Geometric mean primary-particle radius | positive real |
| `rp_gstd` | Geometric standard deviation of particle radius | `>= 1`; use `1.0` for monodisperse |
| `Quantity_aggregates` | Number of successful aggregates to write | integer `>= 1` |
| `Ext_case` | Extreme-case switch | `0` or `1` |
| `Nsubcl_perc` | Initial sub-cluster fraction | `(0, 1]`; normally `0.10` |
| `tol_ov` | Numerical tolerance for **unintended** overlap | positive real; normally `1.0e-6` |
| `overlap_mode` | Intended contact-overlap model | `'none'`, `'fixed'`, or `'statistical'` |
| `overlap_fraction` | Fixed intended-contact overlap | fraction of `Ri+Rj`; `0.05` = 5% |
| `overlap_mean` | Statistical overlap mean | fraction of `Ri+Rj` |
| `overlap_std` | Statistical overlap standard deviation | non-negative fraction |
| `overlap_max` | Statistical hard upper bound | fraction in `(0,0.95)` |
| `random_seed_value` | Fortran RNG seed | `-1` for runtime default; `>=0` for reproducible runs |
| `output_dir` | Directory receiving `.dat` files | quoted text; created automatically |


### Intended contact overlap

Overlap is applied **only to the selected particle-particle contact used to join a monomer or cluster**. Other particle pairs remain subject to the strict `tol_ov` collision check. This prevents the overlap option from becoming a blanket permission for unrelated particles to interpenetrate.

No overlap (legacy behavior):

```text
overlap_mode = 'none'
```

Fixed 5% overlap at every intended contact:

```text
overlap_mode     = 'fixed'
overlap_fraction = 0.05
```

Statistical overlap, sampled independently per intended contact from a normal distribution bounded to `[0, overlap_max]`:

```text
overlap_mode = 'statistical'
overlap_mean = 0.05
overlap_std  = 0.02
overlap_max  = 0.12
```

The overlap fraction is dimensionless. For two particles, the intended contact center distance is `(Ri + Rj) * (1 - overlap)`. Thus `0.05` means a 5% reduction relative to the touching center distance.

Because overlap changes particle-center geometry, it can change measured geometric quantities such as radius of gyration. Treat overlap parameters as part of the physical aggregate model and record them with simulation results. Large overlap values can also make some requested FracVAL configurations harder or impossible to construct.

### Monodisperse example

```text
&fracval
    N                   = 100
    Df                  = 1.79
    kf                  = 1.40
    rp_g                = 15.0
    rp_gstd             = 1.00
    Quantity_aggregates = 1
    Ext_case            = 0
    Nsubcl_perc         = 0.10
    tol_ov              = 1.0e-6
    random_seed_value   = 12345
    output_dir          = 'tests/monodisperse/results'
/
```

### Polydisperse example

```text
&fracval
    N                   = 100
    Df                  = 1.68
    kf                  = 0.98
    rp_g                = 15.0
    rp_gstd             = 2.00
    Quantity_aggregates = 1
    Ext_case            = 0
    Nsubcl_perc         = 0.10
    tol_ov              = 1.0e-6
    random_seed_value   = 67890
    output_dir          = 'tests/polydisperse/results'
/
```

---

## 5. Run

### Default input

If `fracval.in` is in the current directory:

```bash
./build/fracval
```

Windows:

```bat
build\fracval.exe fracval.in
```

or equivalently:

```bash
make run
```

### Named input file

Keep separate configurations for different simulations:

```bash
./build/fracval cases/case_A.in
./build/fracval cases/case_B.in
```

With the Makefile:

```bash
make run INPUT=tests/polydisperse/fracval.in
```

### Help

```bash
./build/fracval --help
```

At startup FracVAL prints the values it actually loaded, including the selected
input file and output directory.

---

## 6. Output files

Each successful aggregate is written to `output_dir` using the pattern:

Relative `output_dir` paths are interpreted relative to the directory from which you launch FracVAL.

```text
N_00000100_Agg_00000001.dat
N_00000100_Agg_00000002.dat
...
```

For example, with:

```text
N = 100
Quantity_aggregates = 50
output_dir = 'runs/case_01'
```

FracVAL writes 50 aggregate files under `runs/case_01/`.

Each line contains one spherical primary particle:

```text
x  y  z  radius
```

There is no header in the native output file so it remains compatible with the
existing FracVAL data format.

Each aggregate also writes a contact-history sidecar:

```text
N_00000100_Agg_00000001.contacts.csv
```

with columns:

```text
contact_index,overlap_fraction
```

A completed tree-like aggregate contains `N-1` intended contacts. In `none` mode these values are zero; fixed/statistical modes record the actual target overlap used for each joining contact.

If an output file with the same name already exists, the new run replaces it.
Use a different `output_dir` for each case when keeping multiple runs.

---

## 7. Tests

The bundled monodisperse, polydisperse, fixed-overlap, and statistical-overlap
smoke tests live in `tests/python/test_fortran_cli.py`. Run them with:

```bash
python -m pytest tests/python/test_fortran_cli.py
```

or, with the Makefile:

```bash
make fortran-test
```

The tests verify that:

- FracVAL runs successfully with runtime input files.
- Each example produces one `.dat` aggregate.
- Each output contains `N=100` rows and four columns.
- The monodisperse case has one particle radius.
- The polydisperse case contains varying particle radii.
- Fixed 5% overlap produces `N-1` 5% intended contacts.
- Statistical overlap remains within its configured bound and varies across contacts.

Outputs are left in:

```text
tests/monodisperse/results/
tests/polydisperse/results/
tests/overlap_fixed/results/
tests/overlap_statistical/results/
```

The stochastic aggregation algorithm may report one or more restart messages
before a successful aggregate is produced. A restart is not by itself a test
failure.

---

## 8. Visualization

### Interactive 3D spheres

Plotly is the default backend. The following renders the primary particles as
true sphere meshes that can be rotated, zoomed, and inspected interactively:

```bash
python3 plot/plot_aggregate.py \
  tests/polydisperse/results/N_00000100_Agg_00000001.dat
```

### Faster interactive mode

For large aggregates, center-marker mode is much lighter:

```bash
python3 plot/plot_aggregate.py aggregate.dat --mode centers
```

### Save interactive HTML

```bash
python3 plot/plot_aggregate.py aggregate.dat --output aggregate.html
```

The generated HTML is self-contained and can be opened directly in a browser.

### Static 3D image

```bash
python3 plot/plot_aggregate.py aggregate.dat \
  --backend matplotlib --output aggregate.png
```

### Jupyter notebook

Start JupyterLab from the project root:

```bash
jupyter lab plot/plot_aggregate.ipynb
```

The notebook loads both bundled test outputs and creates interactive Plotly 3D
views. Run `make test` first if those `.dat` files are missing.

### Plot smoke test

To exercise both plotting backends after installing the Python requirements:

```bash
make plot-test
```

This writes temporary preview files under `build/`.

---

## 9. Directory layout

```text
FracVAL-Qt/
├── Makefile
├── README.md
├── pyproject.toml
├── fracval.in
├── src/                         # Fortran sources + F2PY-facing wrapper
├── build/                       # generated compiler products
├── results/
├── tools/
│   └── build.py                 # cross-platform build script
├── python/
│   └── fracval/
│       ├── desktop/             # PySide6 window, viewer and worker
│       ├── engine.py
│       ├── aggregate.py
│       └── visualization.py
├── gui/                         # source-tree desktop launcher
├── tests/
│   ├── monodisperse/
│   ├── polydisperse/
│   └── python/                  # pytest suite, incl. test_fortran_cli.py
├── plot/                        # scripts and Jupyter notebooks
└── doc/
    ├── USAGE.md
    └── PYTHON_GUI.md
```

---

## 10. Recommended workflow for parameter studies

1. Build once with `make`.
2. Copy `fracval.in` to one input file per case.
3. Give every case a distinct `output_dir`.
4. Run each input through the same `build/fracval` executable.
5. Use the Python plotting tools on any generated `.dat` file.

For example:

```bash
./build/fracval cases/df_168.in
./build/fracval cases/df_180.in
./build/fracval cases/df_200.in
```

No source edit or recompilation is required between those runs.


## 11. Python API and native GUI

For on-demand generation from Python and the native PySide6/Qt desktop GUI,
see [`PYTHON_GUI.md`](PYTHON_GUI.md). The Python extension calls the same
Fortran PCA/CCA numerical routines in memory and supports reproducible seeds,
batch generation, derived geometry, interactive 3-D visualization, and desktop exports.
