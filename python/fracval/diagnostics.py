"""Runtime diagnostics for FracVAL-Qt Python integrations."""
from __future__ import annotations

import importlib.util
import platform
from pathlib import Path
import sys
from typing import Any

from ._toolchain import Compiler, discover_toolchain, install_hint
from .engine import available_backends, extension_available


def _compiler_dict(compiler: Compiler | None) -> dict[str, str] | None:
    if compiler is None:
        return None
    return {"path": str(compiler.path), "version": compiler.version}


def runtime_info() -> dict[str, Any]:
    """Return a JSON-friendly summary of the active FracVAL environment."""
    package_dir = Path(__file__).resolve().parent
    ext_spec = importlib.util.find_spec("fracval._fracval_fortran")
    toolchain = discover_toolchain()
    return {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "fracval_package": str(package_dir),
        "extension_available": extension_available(),
        "extension_path": getattr(ext_spec, "origin", None) if ext_spec else None,
        "available_backends": available_backends(),
        "fortran_compiler": _compiler_dict(toolchain.fortran),
        "c_compiler": _compiler_dict(toolchain.c),
    }


def _compiler_line(value: dict[str, str] | None) -> str:
    if value is None:
        return "not found"
    return f"{value['path']} ({value['version']})"


def format_runtime_info() -> str:
    """Return :func:`runtime_info` as readable diagnostic text."""
    info = runtime_info()
    lines = [
        "FracVAL-Qt runtime diagnostics",
        f"  Python executable   : {info['python_executable']}",
        f"  Python version      : {info['python_version']}",
        f"  Platform            : {info['platform']}",
        f"  Machine             : {info['machine']}",
        f"  Package directory   : {info['fracval_package']}",
        f"  Fortran compiler    : {_compiler_line(info['fortran_compiler'])}",
        f"  C compiler          : {_compiler_line(info['c_compiler'])}",
        f"  F2PY extension      : {'available' if info['extension_available'] else 'not built'}",
        f"  Extension path      : {info['extension_path'] or '-'}",
        f"  Available backends  : {', '.join(info['available_backends']) or 'none'}",
    ]
    if info["fortran_compiler"] is None or info["c_compiler"] is None:
        lines.append(f"  Install compilers   : {install_hint()}")
    if not info["available_backends"]:
        lines.append("  Next step           : python tools/build.py all")
    return "\n".join(lines)


def main() -> None:
    print(format_runtime_info())


if __name__ == "__main__":
    main()
