#!/usr/bin/env python3
"""Compatibility shim: the build logic now lives in tools/build.py.

Equivalent to `python tools/build.py ext`. Kept so older instructions and
scripts keep working.
"""
from pathlib import Path
import runpy
import sys

sys.argv = [sys.argv[0], "ext", *sys.argv[1:]]
runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools" / "build.py"), run_name="__main__")
