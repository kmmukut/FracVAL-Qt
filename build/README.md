# Build directory

Compiler-generated `.o`, `.mod`, the standalone `fracval` executable, F2PY
intermediates, and local plot smoke-test files are created here by the Makefile.
They are not shipped as platform-specific binaries in release archives.

`tools/build.py` writes executable objects to `build/obj/` and extension
intermediates to `build/python_ext/`; setuptools uses `build/setuptools/`.
