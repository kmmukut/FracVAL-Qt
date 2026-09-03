"""Standalone-executable smoke tests (port of the former tests/run_tests.sh).

Each case runs build/fracval[.exe] on a committed namelist with the repository
root as working directory, because the namelists use relative output_dir
values, then checks the .dat and .contacts.csv outputs with NumPy.
"""
from __future__ import annotations

from pathlib import Path
import subprocess

import numpy as np
import pytest

from fracval.engine import _find_executable

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def executable() -> Path:
    exe = _find_executable(None, required=False)
    if exe is None:
        pytest.skip("standalone FracVAL executable not built (run: python tools/build.py exe)")
    return exe


def _run_case(executable: Path, name: str) -> tuple[np.ndarray, np.ndarray]:
    case_dir = ROOT / "tests" / name
    result_dir = case_dir / "results"
    result_dir.mkdir(exist_ok=True)
    for old in list(result_dir.glob("*.dat")) + list(result_dir.glob("*.contacts.csv")):
        old.unlink()

    proc = subprocess.run(
        [str(executable), str(case_dir / "fracval.in")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=600, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    dats = sorted(result_dir.glob("*.dat"))
    assert len(dats) == 1, f"expected 1 aggregate file, found {len(dats)}"
    data = np.loadtxt(dats[0], ndmin=2)
    assert data.shape[1] == 4, "output must contain exactly four columns (x y z radius)"

    contacts_path = dats[0].with_name(dats[0].name[:-4] + ".contacts.csv")
    assert contacts_path.is_file(), f"contact-overlap sidecar not found: {contacts_path}"
    contacts = np.loadtxt(contacts_path, delimiter=",", skiprows=1, ndmin=2)
    return data, contacts


@pytest.mark.parametrize("name,kind", [("monodisperse", "mono"), ("polydisperse", "poly")])
def test_size_distribution_cases(executable, name, kind):
    data, contacts = _run_case(executable, name)
    assert data.shape[0] == 100
    radii = data[:, 3]
    if kind == "mono":
        assert np.ptp(radii) <= 1e-5, "monodisperse case contains varying radii"
    else:
        assert np.ptp(radii) > 1e-5, "polydisperse case did not produce varying radii"
    assert contacts.shape[0] == 99, "expected N-1 intended contacts"


def test_fixed_overlap(executable):
    data, contacts = _run_case(executable, "overlap_fixed")
    assert data.shape[0] == 30
    assert contacts.shape[0] == 29
    assert np.allclose(contacts[:, 1], 0.05, atol=1e-5), "fixed-overlap contacts are not all 5%"


def test_statistical_overlap(executable):
    data, contacts = _run_case(executable, "overlap_statistical")
    values = contacts[:, 1]
    assert data.shape[0] == 30
    assert contacts.shape[0] == 29
    assert np.all(values >= 0.0) and np.all(values <= 0.120001), "statistical overlap out of bounds"
    assert np.ptp(values) > 0.001, "statistical overlap has no variation"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
