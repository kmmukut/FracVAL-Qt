# Integrating FracVAL into another Python project

FracVAL is designed so downstream code depends on the Python API, not on the Qt
GUI or Fortran source layout.

## 1. Install it into the same environment

For development from a local clone:

```bash
cd /path/to/FracVAL-Qt
python3 -m venv .venv
source .venv/bin/activate
make install PYTHON=python
```

For an application that also needs the desktop GUI:

```bash
make install-gui PYTHON=python
```

The current source distribution builds the native F2PY extension locally. The
extension is platform/Python specific and therefore is intentionally not stored
in the source ZIP.

After installation, another Python project in the same environment simply uses:

```python
from fracval import FracVALConfig, generate
```

No GUI imports are required.

## 2. Wrap FracVAL behind your own application API

A good integration pattern is to isolate FracVAL configuration in one function
or service:

```python
from fracval import FracVALConfig, generate


def generate_particles(case):
    config = FracVALConfig(
        n=case.n,
        df=case.fractal_dimension,
        kf=case.fractal_prefactor,
        rp_g=case.primary_radius,
        rp_gstd=case.radius_gstd,
        seed=case.seed,
    )
    aggregate = generate(config)
    return aggregate.data.copy()
```

The rest of your solver sees only an `(N,4)` NumPy array and does not depend on
FracVAL's UI or file format.

## 3. Prefer fixed seeds in scientific workflows

For a parameter study, make the seed part of the case definition and record it
with results. `seed=None` is useful for exploratory GUI work; fixed seeds are
better for reproducible research.

`generate_batch()` and `iter_generate_batch()` derive deterministic
per-aggregate seeds from the base seed, so rerunning a batch with the same base
configuration reproduces its seed sequence.

## 4. Persist configuration and provenance

Configuration-only JSON:

```python
config.save_json("case.json")
config = FracVALConfig.load_json("case.json")
```

Complete result bundle:

```python
from fracval import save_bundle, load_bundle

paths = save_bundle(aggregate, "results", stem="case01_aggregate0001")
aggregate_again = load_bundle(paths["json"])
```

A bare native `.dat` file contains only `x y z radius`; it does not preserve
`Df`, `kf`, seed, overlap settings or backend. Prefer bundles for long-lived
results.

## 5. Backend selection

For normal use:

```python
aggregate = generate(config, backend="auto")
```

`auto` prefers the F2PY extension because it avoids temporary files and returns
arrays directly. If your deployment cannot build the extension, compile the
standalone executable and either let FracVAL discover `build/fracval` or set:

```bash
export FRACVAL_EXECUTABLE=/absolute/path/to/fracval
```

Then `backend="auto"` can fall back to the executable.

Use `fracval-info` in deployment diagnostics.

## 6. Threading and multiprocessing

The legacy Fortran core uses module-global state. The Python extension therefore
serializes calls with an internal lock. It is safe for a GUI worker thread to
call FracVAL while the UI remains responsive, but multiple Python threads do not
execute the Fortran generator concurrently.

For parallel parameter sweeps, use **multiple processes**, each with its own
process memory, rather than expecting thread-level Fortran concurrency. Start
with small process counts and validate reproducibility/performance on the target
machine.

## 7. Extending the Python layer

Add analysis or export code in Python whenever it does not need to modify the
aggregation algorithm. For example:

```python
import numpy as np


def radial_extent(aggregate):
    center = aggregate.center_of_mass
    return np.linalg.norm(aggregate.xyz - center, axis=1)
```

This keeps scientific generation isolated from post-processing.

If a new setting changes PCA/CCA geometry, propagate it through all layers:

1. runtime state and validation in `src/Ctes.f90`;
2. the relevant PCA/CCA routine;
3. `src/fracval_python_api.f90`;
4. `python/fracval/_fracval_fortran.pyf`;
5. `FracVALConfig` and `engine.py`;
6. Qt controls if it should be interactive;
7. standalone namelist parsing if CLI users need it;
8. deterministic tests and documentation.

Do not add scientific behavior only in the GUI. The GUI should remain a client
of the same public API used by scripts.

## 8. Recommended project boundary

Keep imports like this:

```text
your_project/
    simulation.py  --->  fracval.FracVALConfig / fracval.generate
    analysis.py    --->  Aggregate or NumPy arrays
    ui.py          --->  your own UI (optional)
```

Avoid importing `fracval.desktop.*` unless you are intentionally extending the
shipped Qt application.

## 9. Example files

See `examples/python/06_embed_in_your_project.py` for a minimal wrapper and
`examples/python/05_parameter_sweep.py` for a reproducible sweep template.
