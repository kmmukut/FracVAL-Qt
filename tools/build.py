#!/usr/bin/env python3
"""Cross-platform build tool for the FracVAL executable and F2PY extension.

    python tools/build.py exe     # build/fracval[.exe]
    python tools/build.py ext     # python/fracval/_fracval_fortran.<EXT_SUFFIX>
    python tools/build.py all
    python tools/build.py clean

The F2PY extension is built without Meson: F2PY only generates wrapper sources,
which are compiled together with the Fortran core by gfortran and gcc/clang.
On Windows the MinGW-w64 GNU toolchain from conda-forge is required.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import struct
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PKG = ROOT / "python" / "fracval"
BUILD = ROOT / "build"
EXE_OBJ = BUILD / "obj"
EXT_BUILD = BUILD / "python_ext"
EXT_GEN = EXT_BUILD / "generated"
EXT_OBJ = EXT_BUILD / "obj"
PYF = PKG / "_fracval_fortran.pyf"

if str(ROOT / "python") not in sys.path:
    sys.path.insert(0, str(ROOT / "python"))


def _load_toolchain():
    """Load fracval/_toolchain.py directly.

    Importing `fracval._toolchain` would execute the package's __init__, which needs
    NumPy; the `exe` subcommand must work before any Python packages are installed.
    """
    spec = importlib.util.spec_from_file_location("fracval_toolchain", PKG / "_toolchain.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_toolchain = _load_toolchain()
Compiler = _toolchain.Compiler
discover_toolchain = _toolchain.discover_toolchain
install_hint = _toolchain.install_hint
is_msvc = _toolchain.is_msvc

# Compile order matters: Fortran modules must be compiled before their users.
# tests/python/test_build_tool.py asserts the Makefile uses the same order.
CORE_SOURCES = (
    "Ctes.f90", "random.f90", "RAND_SAMPLE.f90", "a_Random_PP.f90",
    "PCA_cca.f90", "PCA_Subclusters_module.f90", "Save_results_CC.f90", "CCA_module.f90",
)
EXE_SOURCES = CORE_SOURCES + ("Frac_VAL_CCA.f90",)
EXT_SOURCES = CORE_SOURCES + ("fracval_python_api.f90",)
RUNTIME_DLLS = ("libgfortran-5.dll", "libquadmath-0.dll", "libgcc_s_seh-1.dll", "libwinpthread-1.dll")
DEBUG_FFLAGS = "-O0 -g -Wall -Wextra -fcheck=all -fbacktrace"

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"


# ---------- platform rules ----------

def executable_path() -> Path:
    return BUILD / ("fracval.exe" if IS_WINDOWS else "fracval")


def extension_path() -> Path:
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or (".pyd" if IS_WINDOWS else ".so")
    return PKG / ("_fracval_fortran" + suffix)


def fortran_flags(base: str, *, shared: bool) -> list[str]:
    flags = shlex.split(base)
    if shared and not IS_WINDOWS:
        flags.append("-fPIC")
    return flags


def c_flags(includes: list[str], *, bits: int = struct.calcsize("P") * 8) -> list[str]:
    flags = ["-O2"]
    if not IS_WINDOWS:
        flags.append("-fPIC")
    if IS_WINDOWS and bits == 64:
        flags.append("-DMS_WIN64")
    flags.extend(f"-I{path}" for path in includes)
    return flags


def executable_link_flags() -> list[str]:
    return ["-static"] if IS_WINDOWS else []


def extension_link_flags() -> list[str]:
    if IS_MACOS:
        return ["-bundle", "-undefined", "dynamic_lookup"]
    if IS_WINDOWS:
        return ["-shared", "-static-libgfortran", "-static-libgcc", "-static-libquadmath"]
    return ["-shared"]


def python_import_library() -> Path | None:
    """CPython import library needed when MinGW links the extension on Windows."""
    if not IS_WINDOWS:
        return None
    tag = f"{sys.version_info.major}{sys.version_info.minor}"
    lib = Path(sys.base_prefix) / "libs" / f"python{tag}.lib"
    if not lib.is_file():
        raise SystemExit(f"Python import library not found: {lib}")
    return lib


def verification_env(exclude_dirs: list[Path]) -> dict[str, str]:
    """Environment for the post-link import check: PATH without the compiler dirs."""
    excluded = {d.resolve() for d in exclude_dirs}
    env = dict(os.environ)
    entries = []
    for entry in env.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        try:
            if Path(entry).resolve() in excluded:
                continue
        except OSError:
            pass
        entries.append(entry)
    env["PATH"] = os.pathsep.join(entries)
    env["PYTHONPATH"] = str(ROOT / "python")
    return env


# ---------- helpers ----------

def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(shlex.quote(str(x)) for x in cmd), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=str(cwd or ROOT), check=True)


def require(toolchain, kind: str) -> Compiler:
    compiler = getattr(toolchain, kind)
    if compiler is None:
        raise SystemExit(
            f"No {kind.upper() if kind == 'c' else 'Fortran'} compiler found. Searched:\n  "
            + "\n  ".join(toolchain.searched)
            + f"\nInstall one with:\n  {install_hint()}"
        )
    if kind == "c" and IS_WINDOWS and is_msvc(compiler):
        raise SystemExit(
            "MSVC cl.exe cannot be combined with gfortran for the FracVAL extension.\n"
            "Install the MinGW-w64 GNU toolchain instead:\n  " + install_hint()
        )
    return compiler


# ---------- build steps ----------

def compile_fortran(fc: Path, flags: list[str], sources: tuple[str, ...], objdir: Path) -> list[Path]:
    objdir.mkdir(parents=True, exist_ok=True)
    objects: list[Path] = []
    for name in sources:
        obj = objdir / (Path(name).stem + ".o")
        run([fc, *flags, f"-J{objdir}", f"-I{objdir}", "-c", SRC / name, "-o", obj])
        objects.append(obj)
    return objects


def build_executable(fc: Path, fflags: str) -> Path:
    flags = fortran_flags(fflags, shared=False)
    objects = compile_fortran(fc, flags, EXE_SOURCES, EXE_OBJ)
    target = executable_path()
    run([fc, *flags, *objects, *executable_link_flags(), "-o", target])
    print(f"Built: {target.relative_to(ROOT)}")
    return target


def remove_existing_extension(target: Path) -> None:
    try:
        target.unlink(missing_ok=True)
        for dll in target.parent.glob("*.dll"):
            dll.unlink()
    except PermissionError as exc:
        raise SystemExit(
            f"Cannot replace {target.name}: the file is in use. Close running FracVAL/Python "
            "processes that have the extension loaded (GUI, notebooks) and retry."
        ) from exc


def copy_runtime_dlls(compiler_dir: Path, dest: Path) -> list[Path]:
    """Copy the gfortran runtime DLLs next to the extension (Windows fallback)."""
    copied: list[Path] = []
    for name in RUNTIME_DLLS:
        source = compiler_dir / name
        if source.is_file():
            shutil.copy2(source, dest / name)
            copied.append(dest / name)
    return copied


def verify_extension_import(exclude_dirs: list[Path]) -> tuple[bool, str]:
    """Import the built extension in a clean subprocess; return (ok, output)."""
    code = "import fracval._fracval_fortran as m; print(m.__file__)"
    proc = subprocess.run(
        [sys.executable, "-c", code], env=verification_env(exclude_dirs),
        cwd=str(BUILD), capture_output=True, text=True, check=False,
    )
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def build_extension(fc: Path, cc: Path, fflags: str) -> Path:
    import numpy as np  # deferred so `exe` works in environments without NumPy

    shutil.rmtree(EXT_BUILD, ignore_errors=True)
    EXT_GEN.mkdir(parents=True)
    EXT_OBJ.mkdir(parents=True)

    run([sys.executable, "-m", "numpy.f2py", PYF, "--build-dir", EXT_GEN])

    flags = fortran_flags(fflags, shared=True)
    objects = compile_fortran(fc, flags, EXT_SOURCES, EXT_OBJ)
    wrapper = EXT_GEN / "_fracval_fortran-f2pywrappers.f"
    wrapper_obj = EXT_OBJ / "f2pywrappers.o"
    run([fc, *flags, "-c", wrapper, "-o", wrapper_obj])
    objects.append(wrapper_obj)

    f2py_src = Path(np.f2py.__file__).resolve().parent / "src"
    includes = [sysconfig.get_paths()["include"], np.get_include(), str(f2py_src)]
    cflags = c_flags(includes)
    module_obj = EXT_OBJ / "module.o"
    fobject_obj = EXT_OBJ / "fortranobject.o"
    run([cc, *cflags, "-c", EXT_GEN / "_fracval_fortranmodule.c", "-o", module_obj])
    run([cc, *cflags, "-c", f2py_src / "fortranobject.c", "-o", fobject_obj])
    objects.extend([module_obj, fobject_obj])

    target = extension_path()
    remove_existing_extension(target)
    link = [fc, *extension_link_flags(), *objects]
    import_library = python_import_library()
    if import_library is not None:
        link.append(import_library)
    link.extend(["-o", target])
    run(link)

    exclude = [fc.parent, cc.parent]
    ok, output = verify_extension_import(exclude)
    if not ok and IS_WINDOWS:
        copied = copy_runtime_dlls(fc.parent, target.parent)
        print("Import check failed; copied runtime DLLs beside the extension: "
              + (", ".join(p.name for p in copied) or "none found"))
        ok, output = verify_extension_import(exclude)
    if not ok:
        raise SystemExit("The extension was linked but cannot be imported:\n" + output)
    print(f"Built: {target.relative_to(ROOT)}")
    return target


def clean() -> None:
    for directory in (EXE_OBJ, EXT_BUILD, BUILD / "setuptools", BUILD / "lib"):
        shutil.rmtree(directory, ignore_errors=True)
    for bdist in BUILD.glob("bdist.*"):
        shutil.rmtree(bdist, ignore_errors=True)
    for pattern in ("*.o", "*.mod", "*.png", "*.html", "fracval", "fracval.exe"):
        for path in BUILD.glob(pattern):
            if path.is_file():
                path.unlink()
    for pattern in ("_fracval_fortran*.so", "_fracval_fortran*.dylib", "_fracval_fortran*.pyd", "*.dll"):
        for path in PKG.glob(pattern):
            path.unlink()
    (BUILD / ".gitkeep").touch()
    print("Cleaned native build products.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("exe", "ext", "all", "clean"))
    parser.add_argument("--fc", help="Fortran compiler (default: $FC, then gfortran on PATH)")
    parser.add_argument("--cc", help="C compiler (default: $CC, then gcc/clang on PATH)")
    parser.add_argument("--fflags", default=os.environ.get("FFLAGS", "-O2"),
                        help="Fortran optimisation/warning flags (default: $FFLAGS or -O2)")
    parser.add_argument("--debug", action="store_true", help=f"use '{DEBUG_FFLAGS}'")
    args = parser.parse_args(argv)

    if args.command == "clean":
        clean()
        return 0

    fflags = DEBUG_FFLAGS if args.debug else args.fflags
    toolchain = discover_toolchain(fc=args.fc, cc=args.cc)
    fc = require(toolchain, "fortran")
    print(f"Fortran compiler: {fc.path} ({fc.version})")
    if args.command in ("exe", "all"):
        build_executable(fc.path, fflags)
    if args.command in ("ext", "all"):
        cc = require(toolchain, "c")
        print(f"C compiler      : {cc.path} ({cc.version})")
        build_extension(fc.path, cc.path, fflags)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
