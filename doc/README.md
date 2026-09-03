# FracVAL-Qt documentation index

For the most complete treatment, read:

- **`FracVAL_User_Developer_Guide.pdf`** - compiled detailed manual.
- **`FracVAL_User_Developer_Guide.tex`** - editable LaTeX source for the manual.

Quick references:

- `USAGE.md` - Fortran build, runtime namelist, output files, tests and plotting.
- `PYTHON_GUI.md` - Python API, F2PY backend and native Qt desktop GUI.
- `OVERLAP.md` - intended-contact overlap model, geometry and caveats.
- `API_REFERENCE.md` - compact reference for public Python objects/functions.
- `INTEGRATION.md` - patterns for using FracVAL inside another Python codebase.

Build the PDF manual from the project root with:

```bash
make docs
```

LaTeX intermediates are placed under `build/docs/`; the final PDF is copied
back to `doc/`.

Historical reference:

- `legacy/FracVAL_v1_User_Manual.pdf` - original-package manual retained for comparison.

## Repository provenance

The repository root also contains `LICENSE`, `NOTICE.md`, `CITATION.cff`,
`CITATION.md`, `AUTHORS.md`, and `CONTRIBUTING.md`. These files document the
original FracVAL lineage, GPLv3 licensing, citation practice, and contribution
workflow for FracVAL-Qt.
