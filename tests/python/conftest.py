"""pytest configuration shared by the FracVAL Python tests."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "python") not in sys.path:
    sys.path.insert(0, str(ROOT / "python"))

# The Qt construction smoke test needs PySide6 and a headless platform plugin.
# It stays opt-in so a plain `pytest` never fails on a machine without Qt.
collect_ignore = [] if os.environ.get("FRACVAL_RUN_GUI_TESTS") == "1" else ["test_qt_gui.py"]


@pytest.fixture(scope="session")
def build_tool():
    """Import tools/build.py under a private module name (avoids the PyPI 'build' package)."""
    path = ROOT / "tools" / "build.py"
    if not path.is_file():
        pytest.skip("tools/build.py not present")
    spec = importlib.util.spec_from_file_location("fracval_build_tool", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
