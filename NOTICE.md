# Origin, attribution, and modifications

## Original FracVAL

FracVAL-Qt is a derivative and modernization of the original **FracVAL**
Fortran software developed by **J. Morán, A. Fuentes, F. Liu, and J. Yon**.
The original software accompanies the publication:

> J. Morán, A. Fuentes, F. Liu, and J. Yon, "FracVAL: An improved tunable
> algorithm of cluster-cluster aggregation for generation of fractal
> structures formed by polydisperse primary particles," *Computer Physics
> Communications*, 239 (2019), 225-237.
> DOI: 10.1016/j.cpc.2019.01.015

Original software/data release:

> Morán, J.; Fuentes, A.; Liu, F.; Yon, J. (2019), "FracVAL: An improved
> tunable algorithm of cluster-cluster aggregation for generation of fractal
> structures formed by polydisperse primary particles," Mendeley Data, V1.
> DOI: 10.17632/mgf8wdcsfb.1

The original FracVAL release is distributed under the **GNU General Public
License version 3 (GPLv3)**.

## FracVAL-Qt modifications

This repository preserves and extends the original FracVAL numerical
aggregation code. The modernization layer adds, among other changes:

- runtime configuration instead of recompilation for normal parameter changes;
- an out-of-tree Fortran build;
- deterministic seed control;
- a Python API and F2PY in-memory backend;
- a native PySide6/Qt desktop interface;
- interactive 3-D visualization and export;
- fixed and bounded statistical intended-contact overlap modes;
- tests, examples, diagnostics, and modern user/developer documentation.

The original FracVAL authors should be credited for the original scientific
algorithm and Fortran implementation. The Qt/Python interface, overlap
extensions, packaging, tests, and modern documentation are subsequent
modifications maintained in this repository.

Nothing in this repository should be interpreted as an endorsement of these
later modifications by the original authors.

## License

FracVAL-Qt is distributed under the GNU General Public License version 3.
See `LICENSE` for the complete license text.
