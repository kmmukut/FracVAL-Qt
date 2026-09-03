#!/usr/bin/env python3
"""Build the FracVAL F2PY extension without requiring Meson.

NumPy 2 on Python >=3.12 normally routes `f2py -c` through Meson.  This helper
uses F2PY only to generate wrapper sources, then compiles them directly with the
system C compiler and gfortran.  It works with the ordinary FracVAL Makefile
workflow and keeps all temporary objects under build/python_ext/.
"""
from __future__ import annotations

import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import sysconfig

import numpy as np
import numpy.f2py

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PKG = ROOT / "python" / "fracval"
BUILD = ROOT / "build" / "python_ext"
GEN = BUILD / "generated"
OBJ = BUILD / "obj"
PYF = PKG / "_fracval_fortran.pyf"

FORTRAN = [
    "Ctes.f90", "random.f90", "RAND_SAMPLE.f90", "a_Random_PP.f90",
    "PCA_cca.f90", "PCA_Subclusters_module.f90", "Save_results_CC.f90",
    "CCA_module.f90", "fracval_python_api.f90",
]


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(shlex.quote(x) for x in cmd))
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def main() -> None:
    fc = os.environ.get("FC", "gfortran")
    if shutil.which(fc) is None:
        raise SystemExit(f"Fortran compiler not found: {fc}")
    cc_tokens = shlex.split(sysconfig.get_config_var("CC") or "cc")
    cc = cc_tokens[0]
    if shutil.which(cc) is None:
        raise SystemExit(f"C compiler not found: {cc}")

    shutil.rmtree(BUILD, ignore_errors=True)
    GEN.mkdir(parents=True)
    OBJ.mkdir(parents=True)

    run([sys.executable, "-m", "numpy.f2py", str(PYF), "--build-dir", str(GEN)])

    ff = shlex.split(os.environ.get("F2PY_FFLAGS", "-O2 -fPIC"))
    for name in FORTRAN:
        run([fc, *ff, f"-J{OBJ}", f"-I{OBJ}", "-c", str(SRC / name), "-o", str(OBJ / (Path(name).stem + ".o"))])
    wrapper = GEN / "_fracval_fortran-f2pywrappers.f"
    run([fc, *ff, "-c", str(wrapper), "-o", str(OBJ / "f2pywrappers.o")])

    f2py_src = Path(np.f2py.__file__).resolve().parent / "src"
    includes = [sysconfig.get_paths()["include"], np.get_include(), str(f2py_src)]
    cflags = ["-O2", "-fPIC", *(f"-I{x}" for x in includes)]
    run([cc, *cflags, "-c", str(GEN / "_fracval_fortranmodule.c"), "-o", str(OBJ / "module.o")])
    run([cc, *cflags, "-c", str(f2py_src / "fortranobject.c"), "-o", str(OBJ / "fortranobject.o")])

    ext = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    target = PKG / ("_fracval_fortran" + ext)
    objects = [str(p) for p in sorted(OBJ.glob("*.o"))]
    if platform.system() == "Darwin":
        link = [fc, "-bundle", "-undefined", "dynamic_lookup", *objects, "-o", str(target)]
    else:
        link = [fc, "-shared", *objects, "-o", str(target)]
    run(link)
    print(f"Built: {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
