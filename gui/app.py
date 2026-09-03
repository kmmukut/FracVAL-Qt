#!/usr/bin/env python3
"""Source-tree launcher for the native FracVAL Qt desktop application."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from fracval.desktop.main import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
