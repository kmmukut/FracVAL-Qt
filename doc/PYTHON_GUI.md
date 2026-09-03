# FracVAL-Qt Python API and native Qt GUI

This is the practical guide for users who want either the desktop interface or
the Python library. For architecture, formulas, development guidance, and a
complete reference, see `FracVAL_User_Developer_Guide.pdf`.

## 1. Which interface should I use?

- **Qt GUI**: interactive generation, 3-D inspection, appearance control, export.
- **Python API**: scripts, notebooks, parameter sweeps, downstream applications.
- **Fortran CLI**: compiled namelist-driven jobs without Python orchestration.

The Qt GUI calls the same public Python API used by scripts. The Python API in
turn calls the same Fortran PCA/CCA engine as the standalone executable.

---

## 2. First installation

From the project root, macOS / Linux:

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

Verify the installation:

```bash
fracval-info
fracval-qt-check
python -m pytest
```

---

## 3. Normal GUI launch after installation

You do **not** rebuild FracVAL every time you change parameters.

```bash
cd /path/to/FracVAL-Qt
conda activate fracval
fracval-gui
```

Equivalent source-tree command:

```bash
make gui PYTHON=python
```

Rebuild only after changing Fortran source, changing Python environments, or
moving to a different machine/architecture.

---

## 4. GUI workflow

The left panel controls generation and the right panel is the interactive 3-D
viewer.

### Aggregate parameters

- `N`: number of primary particles.
- `Df`: fractal dimension.
- `kf`: fractal prefactor.
- distribution: monodisperse or polydisperse.
- geometric mean radius (`rp_g`).
- geometric radius standard deviation (`rp_gstd`); monodisperse fixes this to 1.
- number of aggregates in the batch.

### Random seed

Use a fixed base seed for reproducible work. In a batch, FracVAL derives a
deterministic per-aggregate seed sequence from that base seed.

### Contact overlap

Modes:

- **None**: legacy touching contact.
- **Fixed**: one overlap percentage at every intended joining contact.
- **Statistical**: bounded normal overlap with mean, standard deviation and max.

The GUI uses percentages. Python and Fortran input files use fractions, so 5%
is `0.05` in the API.

Unrelated particle pairs remain collision protected by `tol_ov`.

### Advanced

Normally leave:

```text
Ext_case       = 0
Nsubcl_perc    = 0.10
tol_ov         = 1e-6
```

`Max attempts` limits aggregate restarts in the in-memory extension backend.
`Backend=Auto` prefers the F2PY extension and falls back to the standalone
executable if necessary.

### Display and appearance

Rendering:

- **Spheres**: true mesh geometry, best for small/medium aggregates.
- **Centers**: lightweight markers, best for large aggregates.

Appearance controls include:

- solid particle color or color by radius;
- Plotly radius color scale;
- opacity;
- shininess;
- background color;
- XYZ axes/grid visibility (off by default);
- radius legend;
- title.

Appearance changes do not regenerate or alter the aggregate.

### Export

The GUI can save:

- DAT (`x y z radius`);
- CSV;
- contact-overlap CSV;
- XYZ particle centers;
- metadata JSON;
- standalone interactive 3-D HTML;
- complete batch ZIP.

Parameter files saved from the GUI contain the generation configuration, batch
count, selected backend, and appearance settings.

---

## 5. Basic Python API

```python
from fracval import FracVALConfig, generate

config = FracVALConfig(
    n=100,
    df=1.79,
    kf=1.40,
    rp_g=15.0,
    rp_gstd=1.0,
    seed=12345,
)

aggregate = generate(config)
print(aggregate.n)
print(aggregate.data.shape)       # (100, 4)
print(aggregate.radius_of_gyration)
```

Returned arrays:

```python
aggregate.x
aggregate.y
aggregate.z
aggregate.radius
aggregate.xyz    # N x 3
aggregate.data   # N x 4: x, y, z, radius
```

---

## 6. Polydisperse generation

```python
config = FracVALConfig(
    n=100,
    df=1.68,
    kf=0.98,
    rp_g=15.0,
    rp_gstd=2.0,
    seed=67890,
)
aggregate = generate(config)
```

`rp_gstd=1.0` is monodisperse; values above 1 invoke the existing lognormal
primary-particle radius generator.

---

## 7. Overlap from Python

### Fixed 5% intended-contact overlap

```python
config = FracVALConfig(
    n=100,
    seed=12345,
    overlap_mode="fixed",
    overlap_fraction=0.05,
)
aggregate = generate(config)
```

### Statistical overlap

```python
config = FracVALConfig(
    n=100,
    seed=12345,
    overlap_mode="statistical",
    overlap_mean=0.05,
    overlap_std=0.02,
    overlap_max=0.12,
)
aggregate = generate(config)
```

Inspect realized contacts:

```python
print(aggregate.contact_count)
print(aggregate.contact_overlaps)
print(aggregate.mean_contact_overlap)
print(aggregate.std_contact_overlap)
print(aggregate.max_contact_overlap)
```

See `OVERLAP.md` for model details and caveats.

---

## 8. Reusable configuration files

```python
config.save_json("case.json")
config2 = FracVALConfig.load_json("case.json")
```

Create variants without mutating the original:

```python
case_b = config.with_updates(df=1.85, kf=1.25)
case_c = config.with_seed(54321)
```

`FracVALConfig.load_json()` also accepts the richer JSON saved from the GUI and
extracts its nested configuration.

---

## 9. Batch generation

```python
from fracval import generate_batch

aggregates = generate_batch(
    50,
    FracVALConfig(n=100, df=1.79, kf=1.40, seed=12345),
)
```

For progress-oriented workflows use the streaming API:

```python
from fracval import iter_generate_batch

for index, aggregate in enumerate(iter_generate_batch(50, config), start=1):
    print(index, aggregate.seed)
```

This is the same pattern used by the Qt worker.

---

## 10. Save and reload portable result bundles

A native DAT file contains only particle geometry. For scientific provenance,
save the metadata too:

```python
from fracval import save_bundle, load_bundle

paths = save_bundle(
    aggregate,
    "results/case_01",
    stem="aggregate_0001",
)

restored = load_bundle(paths["json"])
```

Default bundle files:

```text
aggregate_0001.dat
aggregate_0001.csv
aggregate_0001.contacts.csv
aggregate_0001.json
```

Optionally add XYZ:

```python
save_bundle(
    aggregate,
    "results/case_01",
    stem="aggregate_0001",
    formats=("dat", "csv", "contacts", "xyz", "json"),
)
```

---

## 11. Python visualization

```python
from fracval import ViewerAppearance, plot_3d

appearance = ViewerAppearance(
    particle_color="#CC5500",
    opacity=0.85,
    shininess=0.75,
    background_color="#FFFFFF",
    show_axes=False,
)

fig = plot_3d(aggregate, mode="spheres", appearance=appearance)
fig.show()
```

Color by radius:

```python
appearance = ViewerAppearance(
    color_mode="radius",
    colorscale="Plasma",
    show_colorbar=True,
    show_axes=False,
)
```

Large aggregate:

```python
fig = plot_3d(aggregate, mode="centers")
```

Static Matplotlib rendering requires the optional plotting dependencies:

```bash
python -m pip install -e '.[plot]'
```

then:

```python
from fracval import plot_static
fig = plot_static(aggregate)
fig.savefig("aggregate.png", dpi=200)
```

---

## 12. Backends

### Extension (preferred)

Build with:

```bash
python tools/build.py ext
```

Python calls the Fortran generator in memory and receives NumPy arrays directly.
The wrapper releases the Python GIL while Fortran runs so a Qt event loop can
remain responsive, but calls are serialized because the legacy Fortran modules
use shared global state.

### Executable (fallback)

Build with:

```bash
python tools/build.py exe
```

The Python engine can run `build/fracval` through a temporary input/output
directory. A custom binary can be supplied to `generate()` or selected with:

```bash
export FRACVAL_EXECUTABLE=/absolute/path/to/fracval
```

### Check what is available

```bash
fracval-info
```

or:

```python
from fracval import available_backends
print(available_backends())
```

---

## 13. Embedding in another Python application

Install FracVAL into the same environment and import the public API only:

```python
from fracval import FracVALConfig, generate


def particle_cloud(n, df, kf, seed):
    aggregate = generate(FracVALConfig(n=n, df=df, kf=kf, seed=seed))
    return aggregate.data.copy()
```

Use multiprocessing, not multiple Python threads, when you want independent
parallel Fortran generation. See `INTEGRATION.md` and
`examples/python/06_embed_in_your_project.py`.

---

## 14. Error handling

```python
from fracval import GenerationError

try:
    aggregate = generate(config)
except (GenerationError, ValueError) as exc:
    print("FracVAL failed:", exc)
```

`ValueError` indicates invalid input. `GenerationError` indicates a backend or
construction failure.

---

## 15. GUI architecture for developers

```text
gui/app.py
   -> fracval.desktop.main
      -> MainWindow
         -> GenerationWorker (QThread worker)
            -> iter_generate_batch()
               -> Fortran extension / executable
         -> AggregateViewer (QWebEngineView)
            -> plot_3d()
```

Files:

- `python/fracval/desktop/main_window.py`: controls, actions, statistics, export.
- `python/fracval/desktop/workers.py`: background batch generation.
- `python/fracval/desktop/viewer.py`: embedded Plotly/WebEngine viewer.
- `python/fracval/desktop/qt_runtime.py`: Qt plugin discovery/configuration.

Do not put new scientific algorithms directly into `main_window.py`; add them to
the public Python layer or Fortran core as appropriate.

---

## 16. Common macOS/Windows Qt problems

If Qt says it cannot find `cocoa` or a headless platform plugin:

```bash
conda activate fracval
which python
python -c "import PySide6; print(PySide6.__file__)"
fracval-qt-check
```

If the active environment contains a broken/incomplete PySide6 install:

```bash
python -m pip uninstall -y PySide6 PySide6_Addons PySide6_Essentials shiboken6
python -m pip install --no-cache-dir PySide6
fracval-qt-check
```

Avoid mixing a Conda `base` PySide6 with a different environment's Python.

On Windows the expected desktop platform plugin is `windows`
(`PySide6/plugins/platforms/qwindows.dll`). `fracval-qt-check` reports it.
A leaked `QT_QPA_PLATFORM=offscreen` from a CI or WSL shell is overridden by
the launcher, and conda Qt variables (`QT_PLUGIN_PATH`) are replaced by the
PySide6 wheel's own plugin directory.
