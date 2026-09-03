# FracVAL desktop GUI

FracVAL's GUI is a native **PySide6 / Qt** desktop application. The window
controls the existing Fortran PCA/CCA engine through the Python API and embeds
an offline Plotly 3-D viewer with Qt WebEngine.

From the project root:

```bash
conda env create -f environment.yml
conda activate fracval
python -m pip install -e '.[gui]'
python tools/build.py all
```

Windows uses `environment-windows.yml` in place of `environment.yml`.

You can also launch it after installation with:

```bash
fracval-gui
```

The application supports single and batch generation, background generation,
progress updates, reproducible seeds, fixed/statistical intended-contact overlap, parameter JSON files, DAT/CSV/contact-CSV/XYZ/JSON exports, batch ZIP export, and interactive offline 3-D HTML export. The viewer hides XYZ axes by default and exposes particle color, opacity, shininess, background, radius coloring, legend, and title controls in an Appearance panel.

See `doc/PYTHON_GUI.md` for the full guide.
