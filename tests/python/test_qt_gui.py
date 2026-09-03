from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

try:
    import PySide6  # noqa: F401
except ModuleNotFoundError:
    # PySide6 is genuinely absent: skip cleanly instead of a collection error.
    # `configure_qt_runtime()` below raises RuntimeError (not ModuleNotFoundError)
    # once PySide6 is missing, so this check must run first. A present-but-broken
    # PySide6 (e.g. the Windows Qt DLL-load failure) still errors loudly below.
    pytest.skip("PySide6 is not installed", allow_module_level=True)

from fracval.desktop.qt_runtime import apply_qt_library_path, configure_qt_runtime

try:
    qt_info = configure_qt_runtime(headless=True)
except Exception as exc:  # pragma: no cover - depends on the local Qt install
    # Re-raise rather than converting to SystemExit: a module-scope SystemExit
    # crashes pytest collection with INTERNALERROR and hides the real cause,
    # which on Windows is usually a Qt DLL-load failure rather than a missing
    # package. The hint goes to stderr; the original traceback is preserved.
    print(f"FAIL: Qt runtime configuration failed: {exc}", file=sys.stderr)
    raise

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - depends on the local Qt install
    # Re-raise rather than converting to SystemExit: a module-scope SystemExit
    # crashes pytest collection with INTERNALERROR and hides the real cause,
    # which on Windows is usually a Qt DLL-load failure rather than a missing
    # package. The hint goes to stderr; the original traceback is preserved.
    print(
        f"Qt import failed ({exc}). If PySide6 is missing, install it with: "
        "python -m pip install -e '.[gui]'",
        file=sys.stderr,
    )
    raise

apply_qt_library_path(qt_info)

from fracval.desktop.main_window import MainWindow


def test_main_window_constructs_headless():
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    cfg = window.current_config()
    assert cfg.n == 100 and cfg.rp_gstd == 1.0, "Qt parameter panel defaults are invalid"
    assert cfg.overlap_mode == "none", "contact overlap should be disabled by default"
    assert not window.overlap_fraction_spin.isEnabled() and not window.overlap_mean_spin.isEnabled()
    assert window.windowTitle() == "FracVAL-Qt Aggregate Generator"
    appearance = window.current_appearance()
    assert not appearance.show_axes, "XYZ axes should be hidden by default"
    assert appearance.color_mode == "solid" and appearance.particle_color == "#4C78A8"
    window.close()
    app.processEvents()
    print(
        "PASS: native Qt GUI constructs successfully "
        f"(platform={qt_info.selected_platform}, plugins={qt_info.platform_dir})"
    )


if __name__ == "__main__":
    test_main_window_constructs_headless()
