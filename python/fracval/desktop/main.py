"""Application entry point for the FracVAL Qt desktop GUI."""
from __future__ import annotations

import os
import sys

from .qt_runtime import apply_qt_library_path, configure_qt_runtime


def main() -> int:
    # Resolve PySide6's own plugins *before* QApplication is constructed. This
    # is especially important on macOS when Conda/Homebrew Qt variables leak
    # into a venv and Qt otherwise reports a platform-plugin path of "".
    try:
        qt_info = configure_qt_runtime(headless=False)
    except (ImportError, RuntimeError) as exc:
        print(
            "FracVAL could not configure the PySide6/Qt runtime:\n"
            f"  {exc}\n\n"
            "Install/reinstall the GUI dependencies with the same Python:\n"
            "  python -m pip install --upgrade --force-reinstall PySide6\n"
            "  python -m pip install -e '.[gui]'",
            file=sys.stderr,
        )
        return 2

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        print(
            "PySide6 is not installed. Install the GUI dependencies with:\n"
            "  python -m pip install -e '.[gui]'",
            file=sys.stderr,
        )
        return 2

    apply_qt_library_path(qt_info)

    # Chromium/WebEngine can otherwise reject execution as root in containers.
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

    from .main_window import MainWindow

    QApplication.setApplicationName("FracVAL")
    QApplication.setOrganizationName("FracVAL")
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
