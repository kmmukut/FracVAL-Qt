"""Qt runtime discovery and platform-plugin setup.

PySide6 normally discovers its bundled Qt plugins automatically. Some macOS
and Windows Python environments (notably Conda/venv combinations or shells
carrying Qt environment variables) can leave Qt with an empty or incompatible
plugin search path. FracVAL resolves the PySide6 wheel's own plugin directory
before the QApplication is created and points Qt at that directory explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import sys
from typing import Iterable


@dataclass(frozen=True)
class QtRuntimeInfo:
    pyside_dir: Path
    plugin_root: Path
    platform_dir: Path
    platforms: tuple[str, ...]
    selected_platform: str | None = None


def _candidate_pyside_dirs() -> Iterable[Path]:
    """Yield plausible PySide6 package directories without importing Qt."""
    spec = importlib.util.find_spec("PySide6")
    if spec is not None:
        if spec.submodule_search_locations:
            for location in spec.submodule_search_locations:
                yield Path(location).resolve()
        if spec.origin:
            yield Path(spec.origin).resolve().parent

    # These fallbacks help editable/Conda installs whose import metadata is
    # unusual, while still preferring the package selected by this Python.
    for base in (Path(sys.prefix), Path(sys.base_prefix)):
        yield base / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "PySide6"
        yield base / "Lib" / "site-packages" / "PySide6"  # Windows layout


def _find_plugin_root(pyside_dir: Path) -> Path | None:
    candidates = (
        pyside_dir / "Qt" / "plugins",
        pyside_dir / "plugins",
    )
    for candidate in candidates:
        if (candidate / "platforms").is_dir():
            return candidate.resolve()
    return None


def _platform_name(path: Path) -> str | None:
    """Return a Qt QPA platform name from a plugin filename."""
    name = path.name.lower()
    for suffix in (".dylib", ".so", ".dll"):
        if suffix in name:
            name = name.split(suffix, 1)[0]
            break
    if name.startswith("libq"):
        name = name[4:]
    elif name.startswith("q"):
        name = name[1:]
    return name or None


def _available_platforms(platform_dir: Path) -> tuple[str, ...]:
    names: set[str] = set()
    if not platform_dir.is_dir():
        return ()
    for entry in platform_dir.iterdir():
        if not entry.is_file():
            continue
        platform = _platform_name(entry)
        if platform:
            names.add(platform)
    return tuple(sorted(names))


def _prefix_plugin_roots() -> Iterable[Path]:
    """Yield common Qt plugin roots used by Conda and system Python layouts."""
    for base in (Path(sys.prefix), Path(sys.base_prefix)):
        yield base / "lib" / "qt6" / "plugins"
        yield base / "lib" / "Qt6" / "plugins"
        yield base / "plugins"
        yield base / "Library" / "plugins"
        yield base / "Library" / "lib" / "qt6" / "plugins"


def desktop_platform() -> str | None:
    """QPA platform plugin FracVAL pins for a visible desktop session on this OS."""
    if sys.platform == "darwin":
        return "cocoa"
    if sys.platform == "win32":
        return "windows"
    return None


def discover_qt_runtime() -> QtRuntimeInfo:
    """Locate platform plugins belonging to the active PySide6/Qt runtime."""
    seen: set[Path] = set()
    checked: list[str] = []
    pyside_dirs = []
    for candidate in _candidate_pyside_dirs():
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        checked.append(str(candidate))
        if candidate.is_dir():
            pyside_dirs.append(candidate)

    if not pyside_dirs:
        raise RuntimeError(
            "PySide6 is not installed for this Python interpreter. Checked:\n  "
            + ("\n  ".join(checked) if checked else "(none)")
        )

    # Prefer plugins physically bundled beside the selected PySide6 package.
    for pyside_dir in pyside_dirs:
        plugin_root = _find_plugin_root(pyside_dir)
        if plugin_root is not None:
            platform_dir = plugin_root / "platforms"
            return QtRuntimeInfo(
                pyside_dir=pyside_dir,
                plugin_root=plugin_root,
                platform_dir=platform_dir,
                platforms=_available_platforms(platform_dir),
            )

    # Conda packages commonly keep Qt plugins at the environment prefix rather
    # than inside site-packages/PySide6. Only consider roots from this Python's
    # own prefix to avoid mixing incompatible Qt installations.
    for plugin_root in _prefix_plugin_roots():
        checked.append(str(plugin_root))
        if (plugin_root / "platforms").is_dir():
            platform_dir = (plugin_root / "platforms").resolve()
            return QtRuntimeInfo(
                pyside_dir=pyside_dirs[0],
                plugin_root=plugin_root.resolve(),
                platform_dir=platform_dir,
                platforms=_available_platforms(platform_dir),
            )

    # QtCore itself can report the compiled-in PluginsPath without constructing
    # QApplication. This is a final fallback for nonstandard PySide6 layouts.
    try:
        from PySide6.QtCore import QLibraryInfo

        plugin_root = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)).resolve()
        checked.append(str(plugin_root))
        if (plugin_root / "platforms").is_dir():
            platform_dir = plugin_root / "platforms"
            return QtRuntimeInfo(
                pyside_dir=pyside_dirs[0],
                plugin_root=plugin_root,
                platform_dir=platform_dir,
                platforms=_available_platforms(platform_dir),
            )
    except Exception:
        pass

    raise RuntimeError(
        "PySide6 is installed, but its Qt platform plugins could not be found. "
        "Checked:\n  "
        + "\n  ".join(dict.fromkeys(checked))
        + "\nReinstall PySide6 with the same Python interpreter used to run FracVAL."
    )


def _prepend_env_path(name: str, path: Path) -> None:
    value = str(path)
    current = os.environ.get(name, "")
    entries = [item for item in current.split(os.pathsep) if item]
    if value not in entries:
        entries.insert(0, value)
    os.environ[name] = os.pathsep.join(entries)


def configure_qt_runtime(*, headless: bool = False) -> QtRuntimeInfo:
    """Configure Qt's plugin paths before QApplication construction.

    The QPA platform plugin path is intentionally *overridden* to the platform
    directory belonging to the active PySide6 package. This avoids accidentally
    loading an incompatible Qt plugin from Conda, Homebrew, PyQt, or another Qt
    installation present in the shell environment.
    """
    info = discover_qt_runtime()

    _prepend_env_path("QT_PLUGIN_PATH", info.plugin_root)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(info.platform_dir)

    selected: str | None = None
    if headless:
        requested = os.environ.get("QT_QPA_PLATFORM", "").strip()
        if requested and requested in info.platforms:
            selected = requested
        else:
            for candidate in ("offscreen", "minimal"):
                if candidate in info.platforms:
                    selected = candidate
                    break
            if selected is None:
                raise RuntimeError(
                    "No headless Qt platform plugin is available. Found: "
                    + (", ".join(info.platforms) or "none")
                )
            os.environ["QT_QPA_PLATFORM"] = selected
    else:
        # A desktop launch pins the native platform plugin. This also neutralizes
        # an inherited offscreen/xcb value from Conda, CI, WSL, or a previous
        # shell configuration. Linux is left to Qt's own xcb/wayland selection.
        pinned = desktop_platform()
        if pinned is not None and pinned in info.platforms:
            os.environ["QT_QPA_PLATFORM"] = pinned
            selected = pinned

    return QtRuntimeInfo(
        pyside_dir=info.pyside_dir,
        plugin_root=info.plugin_root,
        platform_dir=info.platform_dir,
        platforms=info.platforms,
        selected_platform=selected,
    )


def apply_qt_library_path(info: QtRuntimeInfo) -> None:
    """Add the discovered plugin root to Qt's internal library path list."""
    from PySide6.QtCore import QCoreApplication

    QCoreApplication.addLibraryPath(str(info.plugin_root))


def diagnostic_text(info: QtRuntimeInfo | None = None) -> str:
    if info is None:
        info = discover_qt_runtime()
    lines = [
        f"Python executable     : {sys.executable}",
        f"Python version        : {sys.version.split()[0]}",
        f"PySide6 package       : {info.pyside_dir}",
        f"Qt plugin root        : {info.plugin_root}",
        f"QPA platform directory: {info.platform_dir}",
        "QPA platform plugins  : " + (", ".join(info.platforms) or "none"),
    ]
    if info.selected_platform:
        lines.append(f"Selected QPA platform : {info.selected_platform}")
    return "\n".join(lines)


def main() -> int:
    try:
        info = configure_qt_runtime(headless=False)
    except Exception as exc:
        print(f"Qt runtime check FAILED:\n{exc}", file=sys.stderr)
        return 2

    print(diagnostic_text(info))
    expected = desktop_platform()
    if expected and expected not in info.platforms:
        print(
            f"\nWARNING: expected desktop platform plugin '{expected}' was not found.",
            file=sys.stderr,
        )
        return 1
    print("\nQt runtime check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
