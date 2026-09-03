from __future__ import annotations

from pathlib import Path
import re

import fracval

ROOT = Path(__file__).resolve().parents[2]


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1)


def _citation_version() -> str:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    return re.search(r"^version:\s*(\S+)", text, re.MULTILINE).group(1)


def test_versions_agree():
    assert fracval.__version__ == "1.1.0"
    assert _pyproject_version() == fracval.__version__
    assert _citation_version() == fracval.__version__


def test_package_data_ships_built_extension():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = text.split("[tool.setuptools.package-data]", 1)[1].split("\n\n", 1)[0]
    for pattern in ("_fracval_fortran*.so", "_fracval_fortran*.pyd", "*.dll"):
        assert pattern in block


def test_setuptools_build_dir_is_separated():
    text = (ROOT / "setup.cfg").read_text(encoding="utf-8")
    assert "build_base = build/setuptools" in text
