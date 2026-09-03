---
name: Bug report
about: Report a reproducible FracVAL-Qt problem
title: "[bug] "
labels: bug
assignees: ""
---

## What happened?

Describe the observed behavior and what you expected instead.

## Reproduction

Please include the smallest configuration that reproduces the problem.

- FracVAL-Qt version/tag:
- Operating system:
- Python version:
- `gfortran` version:
- Backend (`extension`, `executable`, or `auto`):
- Random seed:
- `N`, `Df`, `kf`:
- `rp_g`, `rp_gstd`:
- Overlap mode/settings:

If possible, attach the configuration JSON or `fracval.in` file.

## Diagnostics

Paste the output of:

```bash
fracval-info
```

For GUI/Qt problems also include:

```bash
fracval-qt-check
```

## Error/output

Paste the traceback, terminal output, or relevant screenshot here.
