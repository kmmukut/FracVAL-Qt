from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from fracval import FracVALConfig, generate, load_bundle, save_bundle, runtime_info  # noqa: E402
from fracval.engine import _find_executable, extension_available  # noqa: E402


def geometric_pair_overlaps(aggregate) -> np.ndarray:
    """Return all positive pair-overlap fractions in the final geometry."""
    values = []
    xyz = aggregate.xyz
    radius = aggregate.radius
    for i in range(aggregate.n):
        for j in range(i):
            distance = np.linalg.norm(xyz[i] - xyz[j])
            radius_sum = radius[i] + radius[j]
            if distance < radius_sum:
                values.append((radius_sum - distance) / radius_sum)
    return np.asarray(values, dtype=float)


BASE_CFG = FracVALConfig(n=50, df=1.79, kf=1.40, rp_g=15.0, rp_gstd=1.0, seed=12345, max_attempts=100)
STAT_CFG = FracVALConfig(
    n=30, seed=24680, overlap_mode="statistical",
    overlap_mean=0.05, overlap_std=0.02, overlap_max=0.12, max_attempts=500,
)


@pytest.fixture(scope="module")
def extension():
    if not extension_available():
        pytest.skip("F2PY extension not built (run: python tools/build.py ext)")


@pytest.fixture(scope="module")
def executable() -> Path:
    exe = _find_executable(None, required=False)
    if exe is None:
        pytest.skip("standalone executable not built (run: python tools/build.py exe)")
    return exe


def test_extension_reproducibility(extension):
    a = generate(BASE_CFG, backend="extension")
    b = generate(BASE_CFG, backend="extension")
    assert np.array_equal(a.data, b.data), "extension is not reproducible for a fixed seed"
    assert np.array_equal(a.contact_overlaps, b.contact_overlaps)
    assert a.n == 50 and np.all(a.radius == 15.0)
    assert a.contact_count == a.n - 1 and not np.any(a.contact_overlaps != 0.0)


def test_extension_matches_executable(extension, executable):
    a = generate(BASE_CFG, backend="extension")
    c = generate(BASE_CFG, backend="executable", executable=executable)
    assert np.allclose(a.data, c.data, rtol=2e-6, atol=2e-5), \
        f"max abs error={float(np.max(np.abs(a.data - c.data)))}"
    assert np.allclose(a.contact_overlaps, c.contact_overlaps, rtol=1e-6, atol=1e-8)


def test_polydisperse_api(extension):
    d = generate(FracVALConfig(n=50, df=1.68, kf=0.98, rp_g=15.0, rp_gstd=2.0, seed=54321), backend="extension")
    assert np.ptp(d.radius) > 1e-5


def test_fixed_overlap_geometry(extension):
    fixed_cfg = FracVALConfig(n=30, seed=24680, overlap_mode="fixed", overlap_fraction=0.05, max_attempts=500)
    fixed = generate(fixed_cfg, backend="extension")
    assert fixed.contact_count == fixed.n - 1
    assert np.allclose(fixed.contact_overlaps, 0.05, atol=2e-7)
    actual = geometric_pair_overlaps(fixed)
    physical = actual[actual > 1e-4]
    assert len(physical) == fixed.n - 1
    assert np.allclose(physical, 0.05, atol=5e-5)


def test_statistical_overlap_geometry(extension):
    stat = generate(STAT_CFG, backend="extension")
    assert stat.contact_count == stat.n - 1
    assert not np.any(stat.contact_overlaps < 0) and not np.any(stat.contact_overlaps > STAT_CFG.overlap_max)
    assert np.ptp(stat.contact_overlaps) > 1e-4
    actual = geometric_pair_overlaps(stat)
    assert np.sum(actual > 1e-4) == stat.n - 1


def test_statistical_overlap_matches_executable(extension, executable):
    stat = generate(STAT_CFG, backend="extension")
    stat_exe = generate(STAT_CFG, backend="executable", executable=executable)
    assert np.allclose(stat.data, stat_exe.data, rtol=2e-6, atol=2e-5)
    assert np.allclose(stat.contact_overlaps, stat_exe.contact_overlaps, rtol=1e-6, atol=1e-8)


def test_config_and_bundle_round_trips(extension, tmp_path):
    a = generate(BASE_CFG, backend="extension")
    cfg_path = BASE_CFG.save_json(tmp_path / "config.json")
    assert FracVALConfig.load_json(cfg_path) == BASE_CFG
    paths = save_bundle(a, tmp_path / "bundle", stem="sample")
    loaded = load_bundle(paths["json"])
    assert np.allclose(a.data, loaded.data, rtol=1e-8, atol=1e-8)
    assert np.allclose(a.contact_overlaps, loaded.contact_overlaps, rtol=1e-8, atol=1e-8)


def test_runtime_diagnostics_detect_extension(extension):
    assert "extension" in runtime_info()["available_backends"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
