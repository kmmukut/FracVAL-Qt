# FracVAL examples

These examples are intentionally small and are meant to be copied into another
Python project. Install FracVAL first from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
make python-ext PYTHON=python
```

Then run any example with the active environment:

```bash
python examples/python/01_basic_generate.py
```

Files:

- `01_basic_generate.py` - generate one reproducible monodisperse aggregate.
- `02_polydisperse_and_plot.py` - generate a polydisperse aggregate and open an interactive Plotly view.
- `03_overlap_models.py` - compare none, fixed, and statistical intended-contact overlap.
- `04_batch_and_export.py` - generate a reproducible batch and save portable bundles.
- `05_parameter_sweep.py` - run a small `Df`/`kf` sweep and write a CSV summary.
- `06_embed_in_your_project.py` - a library-style wrapper function suitable for importing from another application.
- `configs/` - JSON configuration examples loadable with `FracVALConfig.load_json()`.
