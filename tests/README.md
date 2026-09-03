# FracVAL tests

`make test` runs two scientific/core layers:

1. **Standalone Fortran smoke tests** (`run_tests.sh`) generate deterministic
   monodisperse and polydisperse examples plus fixed- and statistical-overlap
   examples. They validate particle counts, radii, `N-1` contact histories,
   fixed 5% overlap, and bounded statistical variation.
2. **Python API tests** (`tests/python/`) build the F2PY extension, check
   fixed-seed reproducibility, compare extension output with the standalone
   executable, validate polydisperse radii, verify fixed/statistical overlap in
   the final geometry, and exercise Plotly rendering.

The overlap geometry test computes all positive pair intersections from the
returned coordinates. In the fixed 5% case it confirms that the `N-1` intended
contacts are approximately 5% overlapped while unrelated particle pairs remain
non-overlapping within numerical tolerance.

The shell harness remains compatible with the stock Bash 3.2 provided by macOS.

After installing the GUI dependencies with `python -m pip install -e '.[gui]'`,
run the native Qt construction smoke test separately:

```bash
make gui-test PYTHON=python
```

That test discovers PySide6's platform plugins, selects `offscreen` or
`minimal`, constructs the PySide6 main window and WebEngine viewer, validates
including the default disabled overlap controls, and exits.
