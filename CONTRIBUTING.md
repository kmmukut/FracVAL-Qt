# Contributing to FracVAL-Qt

Contributions are welcome. Please keep the scientific core, public Python API,
and GUI layers separated so changes remain testable and reproducible.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[gui,dev,plot]'
make
make python-ext PYTHON=python
```

## Before opening a pull request

Run the scientific regression suite:

```bash
make test PYTHON=python
```

If you changed Qt code, also run:

```bash
make qt-check PYTHON=python
make gui-test PYTHON=python
```

If you changed the manual:

```bash
make docs
```

If you changed Fortran numerics, a debug build is strongly recommended:

```bash
make debug
make test PYTHON=python
```

## Design rules

1. Do not put scientific generation logic inside Qt widgets.
2. Keep the public Python API backward-compatible when practical.
3. Add a fixed-seed regression test for changes that affect generated geometry.
4. Document new runtime parameters in the Python API, GUI, and Fortran namelist.
5. Preserve original FracVAL attribution and GPLv3 notices.
6. Do not commit compiler outputs, virtual environments, caches, or local result
   directories.

## Reporting scientific changes

A pull request that intentionally changes aggregate geometry should explain:

- what numerical behavior changed;
- why the change is scientifically justified;
- which fixed-seed outputs changed;
- whether the fractal relation, collision checks, or overlap model is affected.
