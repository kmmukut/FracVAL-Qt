# FracVAL plotting tools

The plotting tools work with both native `.dat` files and aggregates generated
in memory through the Python API.

## Install plotting dependencies

```bash
python3 -m pip install -r plot/requirements.txt
```

## Existing aggregate file

Interactive true-sphere Plotly view (XYZ axes are hidden by default):

```bash
python3 plot/plot_aggregate.py results/N_00000100_Agg_00000001.dat
```

Customize the appearance from the command line:

```bash
python3 plot/plot_aggregate.py aggregate.dat \
  --color '#CC5500' --opacity 0.85 --shininess 0.75 \
  --background '#F5F5F5' --no-title --output aggregate.html
```

Use `--axes` to restore XYZ axes/grid, or `--color-by-radius --colorbar` for
radius-based coloring.

Faster center-marker mode:

```bash
python3 plot/plot_aggregate.py aggregate.dat --mode centers
```

Self-contained interactive HTML:

```bash
python3 plot/plot_aggregate.py aggregate.dat --output aggregate.html
```

Static Matplotlib image:

```bash
python3 plot/plot_aggregate.py aggregate.dat \
  --backend matplotlib --output aggregate.png
```

## Notebooks

- `plot_aggregate.ipynb` visualizes the saved monodisperse and polydisperse test outputs.
- `generate_and_visualize.ipynb` calls the Fortran engine from Python and plots the returned aggregate directly.

For the second notebook, build the extension first:

```bash
make python-ext
jupyter lab plot/generate_and_visualize.ipynb
```
