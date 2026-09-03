# FracVAL-Qt Python API quick reference

The public API is exported from `fracval`:

```python
from fracval import (
    Aggregate,
    FracVALConfig,
    GenerationError,
    ViewerAppearance,
    available_backends,
    extension_available,
    format_runtime_info,
    generate,
    generate_batch,
    iter_generate_batch,
    load_bundle,
    load_data,
    plot_3d,
    plot_static,
    runtime_info,
    save_bundle,
)
```

## `FracVALConfig`

Immutable dataclass containing the physical/numerical generation settings.
Important fields:

- `n`: number of primary particles.
- `df`: fractal dimension.
- `kf`: fractal prefactor.
- `rp_g`: geometric mean primary-particle radius.
- `rp_gstd`: geometric standard deviation; `1.0` is monodisperse.
- `seed`: fixed integer seed or `None` for a fresh seed selected by Python.
- `max_attempts`: maximum aggregate-construction restarts for the F2PY path.
- `overlap_mode`: `"none"`, `"fixed"`, or `"statistical"`.
- `overlap_fraction`: fixed intended-contact overlap fraction.
- `overlap_mean`, `overlap_std`, `overlap_max`: statistical overlap controls.
- `ext_case`, `nsubcl_perc`, `tol_ov`: advanced/legacy engine controls.

Methods:

```python
cfg.validate()
cfg.with_seed(12345)
cfg.with_updates(df=1.8, kf=1.2)
cfg.to_dict()
cfg.save_json("case.json")
FracVALConfig.from_dict(mapping)
FracVALConfig.load_json("case.json")
```

`FracVALConfig.load_json()` can read both a config-only JSON file and the GUI's
saved parameter JSON envelope.

## Generation

```python
agg = generate(config, backend="auto")
```

Backends:

- `auto`: prefer the F2PY extension; use the standalone executable if needed.
- `extension`: require the in-memory Fortran extension.
- `executable`: run the standalone `build/fracval` program in a temporary directory.

Optional custom executable:

```python
agg = generate(config, backend="executable", executable="/path/to/fracval")
```

Batch generation:

```python
items = generate_batch(50, config)

for agg in iter_generate_batch(50, config):
    ...
```

`iter_generate_batch()` is preferred when the caller needs progress reporting,
streaming output, or cooperative cancellation between aggregates.

## `Aggregate`

Particle arrays:

```python
agg.x       # shape (N,)
agg.y
agg.z
agg.radius
agg.xyz     # shape (N, 3)
agg.data    # shape (N, 4): x, y, z, radius
```

Metadata/provenance:

```python
agg.config
agg.seed
agg.attempts
agg.backend
agg.metadata()
```

Derived geometry:

```python
agg.center_of_mass
agg.radius_of_gyration
agg.bounding_radius
```

Contact-overlap data:

```python
agg.contact_overlaps
agg.contact_count
agg.mean_contact_overlap
agg.std_contact_overlap
agg.max_contact_overlap
```

Exports:

```python
agg.save("aggregate.dat")
agg.save("aggregate.csv")
agg.save("aggregate.contacts.csv")
agg.save("aggregate.xyz")
agg.save("aggregate.json")
```

## Result bundles

A result bundle keeps particle data, contact history and metadata together:

```python
paths = save_bundle(agg, "results/case_01", stem="aggregate_0001")
restored = load_bundle(paths["json"])
```

By default `save_bundle()` writes DAT, CSV, contacts CSV and JSON. Add XYZ if
wanted:

```python
save_bundle(agg, "out", formats=("dat", "csv", "contacts", "xyz", "json"))
```

## Loading a native data file

```python
array = load_data("aggregate.dat")
```

This returns a validated NumPy `(N,4)` array. A bare `.dat` file does not
contain the full physical configuration; use bundles when provenance matters.

## Visualization

```python
appearance = ViewerAppearance(
    color_mode="solid",
    particle_color="#4C78A8",
    opacity=0.96,
    shininess=0.55,
    background_color="#FFFFFF",
    show_axes=False,
)
fig = plot_3d(agg, mode="spheres", appearance=appearance)
fig.show()
```

For large aggregates:

```python
fig = plot_3d(agg, mode="centers")
```

Static Matplotlib rendering (requires the `plot` optional dependencies):

```python
fig = plot_static(agg)
fig.savefig("aggregate.png", dpi=200)
```

## Diagnostics

```python
print(format_runtime_info())
info = runtime_info()
print(available_backends())
print(extension_available())
```

Equivalent shell command:

```bash
fracval-info
```

## Exceptions

Generation failures from the Python engine raise `GenerationError`. Parameter
validation raises `ValueError`. A robust integration normally catches both:

```python
try:
    agg = generate(config)
except (GenerationError, ValueError) as exc:
    logger.error("FracVAL failed: %s", exc)
```
