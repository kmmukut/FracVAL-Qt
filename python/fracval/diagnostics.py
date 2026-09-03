"""Runtime diagnostics for FracVAL-Qt Python integrations."""
from __future__ import annotations

import importlib.util
import platform
from pathlib import Path
import sys
from typing import Any

from .engine import available_backends, extension_available


def runtime_info() -> dict[str, Any]:
    """Return a JSON-friendly summary of the active FracVAL environment."""
    package_dir = Path(__file__).resolve().parent
    ext_spec = importlib.util.find_spec("fracval._fracval_fortran")
    return {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "fracval_package": str(package_dir),
        "extension_available": extension_available(),
        "extension_path": getattr(ext_spec, "origin", None) if ext_spec else None,
        "available_backends": available_backends(),
    }


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
        f"  F2PY extension      : {'available' if info['extension_available'] else 'not built'}",
        f"  Extension path      : {info['extension_path'] or '-'}",
        f"  Available backends  : {', '.join(info['available_backends']) or 'none'}",
    ]
    if not info["available_backends"]:
        lines.append("  Next step           : run 'make' and/or 'make python-ext PYTHON=python'")
    return "\n".join(lines)


def main() -> None:
    print(format_runtime_info())
