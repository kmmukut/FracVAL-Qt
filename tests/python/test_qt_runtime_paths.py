from __future__ import annotations

from pathlib import Path
import tempfile

from fracval.desktop.qt_runtime import _available_platforms, _find_plugin_root


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="fracval-qt-runtime-") as tmp:
        pyside = Path(tmp) / "PySide6"
        platforms = pyside / "Qt" / "plugins" / "platforms"
        platforms.mkdir(parents=True)
        for name in ("libqcocoa.dylib", "libqoffscreen.dylib", "libqminimal.dylib"):
            (platforms / name).touch()

        root = _find_plugin_root(pyside)
        if root != (pyside / "Qt" / "plugins").resolve():
            raise SystemExit("FAIL: bundled PySide6 plugin root was not detected")

        found = _available_platforms(platforms)
        if found != ("cocoa", "minimal", "offscreen"):
            raise SystemExit(f"FAIL: unexpected platform-plugin names: {found}")

    print("PASS: Qt runtime plugin-path discovery helpers")


if __name__ == "__main__":
    main()
