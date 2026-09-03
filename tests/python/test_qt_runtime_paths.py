from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

from fracval.desktop import qt_runtime
from fracval.desktop.qt_runtime import (
    QtRuntimeInfo,
    _available_platforms,
    _candidate_pyside_dirs,
    _find_plugin_root,
    _platform_name,
)


def _make_layout(root: Path, plugin_subdir: str, names: tuple[str, ...]) -> Path:
    platforms = root / "PySide6" / plugin_subdir / "platforms"
    platforms.mkdir(parents=True)
    for name in names:
        (platforms / name).touch()
    return platforms


def test_macos_wheel_layout(tmp_path):
    platforms = _make_layout(tmp_path, "Qt/plugins", ("libqcocoa.dylib", "libqoffscreen.dylib", "libqminimal.dylib"))
    assert _find_plugin_root(tmp_path / "PySide6") == (tmp_path / "PySide6" / "Qt" / "plugins").resolve()
    assert _available_platforms(platforms) == ("cocoa", "minimal", "offscreen")


def test_windows_wheel_layout(tmp_path):
    platforms = _make_layout(tmp_path, "plugins", ("qwindows.dll", "qoffscreen.dll", "qminimal.dll"))
    assert _find_plugin_root(tmp_path / "PySide6") == (tmp_path / "PySide6" / "plugins").resolve()
    assert _available_platforms(platforms) == ("minimal", "offscreen", "windows")


def test_platform_names_across_os():
    assert _platform_name(Path("libqxcb.so")) == "xcb"
    assert _platform_name(Path("libqwayland.so")) == "wayland"
    assert _platform_name(Path("qwindows.dll")) == "windows"
    assert _platform_name(Path("libqcocoa.dylib")) == "cocoa"
    assert _platform_name(Path("qoffscreen.dll")) == "offscreen"


def test_windows_site_packages_fallback_is_searched(monkeypatch):
    monkeypatch.setattr(sys, "prefix", r"C:\envs\fracval")
    monkeypatch.setattr(sys, "base_prefix", r"C:\envs\fracval")
    candidates = [str(p) for p in _candidate_pyside_dirs()]
    assert any(c.endswith(os.path.join("Lib", "site-packages", "PySide6")) for c in candidates)


def test_desktop_platform_per_os(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert qt_runtime.desktop_platform() == "cocoa"
    monkeypatch.setattr(sys, "platform", "win32")
    assert qt_runtime.desktop_platform() == "windows"
    monkeypatch.setattr(sys, "platform", "linux")
    assert qt_runtime.desktop_platform() is None


@pytest.fixture
def isolated_environ(monkeypatch):
    """Give configure_qt_runtime a throwaway copy of os.environ."""
    monkeypatch.setattr(os, "environ", dict(os.environ))
    return os.environ


def _fake_info(tmp_path: Path, platforms: tuple[str, ...]) -> QtRuntimeInfo:
    return QtRuntimeInfo(
        pyside_dir=tmp_path, plugin_root=tmp_path / "plugins",
        platform_dir=tmp_path / "plugins" / "platforms", platforms=platforms,
    )


def test_configure_pins_windows_platform(tmp_path, monkeypatch, isolated_environ):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")  # e.g. inherited from CI or WSL
    monkeypatch.setattr(qt_runtime, "discover_qt_runtime", lambda: _fake_info(tmp_path, ("minimal", "offscreen", "windows")))
    info = qt_runtime.configure_qt_runtime(headless=False)
    assert info.selected_platform == "windows"
    assert os.environ["QT_QPA_PLATFORM"] == "windows"
    assert os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] == str(tmp_path / "plugins" / "platforms")


def test_configure_leaves_linux_platform_alone(tmp_path, monkeypatch, isolated_environ):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.setattr(qt_runtime, "discover_qt_runtime", lambda: _fake_info(tmp_path, ("xcb", "offscreen")))
    info = qt_runtime.configure_qt_runtime(headless=False)
    assert info.selected_platform is None
    assert "QT_QPA_PLATFORM" not in os.environ


def test_headless_prefers_offscreen(tmp_path, monkeypatch, isolated_environ):
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.setattr(qt_runtime, "discover_qt_runtime", lambda: _fake_info(tmp_path, ("windows", "minimal", "offscreen")))
    info = qt_runtime.configure_qt_runtime(headless=True)
    assert info.selected_platform == "offscreen"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
