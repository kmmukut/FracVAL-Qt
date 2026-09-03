from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from fracval.desktop.qt_runtime import apply_qt_library_path, configure_qt_runtime

try:
    qt_info = configure_qt_runtime(headless=True)
except Exception as exc:
    raise SystemExit(f"FAIL: Qt runtime configuration failed: {exc}") from exc

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:
    raise SystemExit("FAIL: PySide6 is not installed; install with: python -m pip install -e '.[gui]'") from exc

apply_qt_library_path(qt_info)

from fracval.desktop.main_window import MainWindow


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    cfg = window.current_config()
    if cfg.n != 100 or cfg.rp_gstd != 1.0:
        raise SystemExit("FAIL: Qt parameter panel defaults are invalid")
    if cfg.overlap_mode != "none":
        raise SystemExit("FAIL: contact overlap should be disabled by default")
    if window.overlap_fraction_spin.isEnabled() or window.overlap_mean_spin.isEnabled():
        raise SystemExit("FAIL: overlap value controls should be disabled in none mode")
    if window.windowTitle() != "FracVAL-Qt Aggregate Generator":
        raise SystemExit("FAIL: unexpected Qt main-window title")
    appearance = window.current_appearance()
    if appearance.show_axes:
        raise SystemExit("FAIL: XYZ axes should be hidden by default")
    if appearance.color_mode != "solid" or appearance.particle_color != "#4C78A8":
        raise SystemExit("FAIL: unexpected default particle appearance")
    window.close()
    app.processEvents()
    print(
        "PASS: native Qt GUI constructs successfully "
        f"(platform={qt_info.selected_platform}, plugins={qt_info.platform_dir})"
    )


if __name__ == "__main__":
    main()
