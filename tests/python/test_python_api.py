from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from fracval import FracVALConfig, generate, load_bundle, save_bundle, runtime_info


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


def main() -> None:
    cfg = FracVALConfig(n=50, df=1.79, kf=1.40, rp_g=15.0, rp_gstd=1.0, seed=12345, max_attempts=100)

    a = generate(cfg, backend="extension")
    b = generate(cfg, backend="extension")
    if not np.array_equal(a.data, b.data):
        raise SystemExit("FAIL: extension is not reproducible for a fixed seed")
    if not np.array_equal(a.contact_overlaps, b.contact_overlaps):
        raise SystemExit("FAIL: contact history is not reproducible for a fixed seed")
    if a.n != 50 or not np.all(a.radius == 15.0):
        raise SystemExit("FAIL: extension monodisperse output is invalid")
    if a.contact_count != a.n - 1 or np.any(a.contact_overlaps != 0.0):
        raise SystemExit("FAIL: legacy no-overlap mode did not record N-1 zero-overlap contacts")
    print(f"PASS: extension reproducibility (seed={a.seed}, attempts={a.attempts})")

    exe = ROOT / "build" / "fracval"
    if exe.exists() and os.access(exe, os.X_OK):
        c = generate(cfg, backend="executable", executable=exe)
        if not np.allclose(a.data, c.data, rtol=2e-6, atol=2e-5):
            max_err = float(np.max(np.abs(a.data - c.data)))
            raise SystemExit(f"FAIL: extension/executable mismatch; max abs error={max_err}")
        if not np.allclose(a.contact_overlaps, c.contact_overlaps, rtol=1e-6, atol=1e-8):
            raise SystemExit("FAIL: extension/executable contact histories differ")
        print("PASS: extension matches standalone executable for the same seed")
    else:
        print("SKIP: standalone executable not built")

    d = generate(FracVALConfig(n=50, df=1.68, kf=0.98, rp_g=15.0, rp_gstd=2.0, seed=54321), backend="extension")
    if np.ptp(d.radius) <= 1e-5:
        raise SystemExit("FAIL: polydisperse API case did not vary radii")
    print("PASS: polydisperse Python API generation")

    fixed_cfg = FracVALConfig(
        n=30, seed=24680, overlap_mode="fixed", overlap_fraction=0.05,
        max_attempts=500,
    )
    fixed = generate(fixed_cfg, backend="extension")
    if fixed.contact_count != fixed.n - 1:
        raise SystemExit("FAIL: fixed overlap did not produce N-1 intended contacts")
    if not np.allclose(fixed.contact_overlaps, 0.05, atol=2e-7):
        raise SystemExit("FAIL: fixed contact history is not 5%")
    actual_fixed = geometric_pair_overlaps(fixed)
    physical_fixed = actual_fixed[actual_fixed > 1e-4]
    if len(physical_fixed) != fixed.n - 1 or not np.allclose(physical_fixed, 0.05, atol=5e-5):
        raise SystemExit("FAIL: final fixed-overlap geometry does not realize 5% intended contacts")
    print("PASS: fixed 5% overlap is realized only at intended contacts")

    stat_cfg = FracVALConfig(
        n=30, seed=24680, overlap_mode="statistical",
        overlap_mean=0.05, overlap_std=0.02, overlap_max=0.12,
        max_attempts=500,
    )
    stat = generate(stat_cfg, backend="extension")
    if stat.contact_count != stat.n - 1:
        raise SystemExit("FAIL: statistical overlap did not produce N-1 intended contacts")
    if np.any(stat.contact_overlaps < 0) or np.any(stat.contact_overlaps > stat_cfg.overlap_max):
        raise SystemExit("FAIL: statistical overlap samples exceeded configured bounds")
    if np.ptp(stat.contact_overlaps) <= 1e-4:
        raise SystemExit("FAIL: statistical overlap samples did not vary")
    actual_stat = geometric_pair_overlaps(stat)
    if np.sum(actual_stat > 1e-4) != stat.n - 1:
        raise SystemExit("FAIL: statistical geometry contains unexpected overlapping pairs")
    print(
        "PASS: statistical contact overlap "
        f"(mean={100*stat.mean_contact_overlap:.2f}%, "
        f"std={100*stat.std_contact_overlap:.2f}%, max={100*stat.max_contact_overlap:.2f}%)"
    )

    if exe.exists() and os.access(exe, os.X_OK):
        stat_exe = generate(stat_cfg, backend="executable", executable=exe)
        if not np.allclose(stat.data, stat_exe.data, rtol=2e-6, atol=2e-5):
            raise SystemExit("FAIL: statistical extension/executable geometries differ")
        if not np.allclose(stat.contact_overlaps, stat_exe.contact_overlaps, rtol=1e-6, atol=1e-8):
            raise SystemExit("FAIL: statistical extension/executable contact histories differ")
        print("PASS: statistical overlap matches standalone executable")

    with tempfile.TemporaryDirectory(prefix="fracval-api-test-") as tmp:
        tmp_path = Path(tmp)
        cfg_path = cfg.save_json(tmp_path / "config.json")
        cfg_roundtrip = FracVALConfig.load_json(cfg_path)
        if cfg_roundtrip != cfg:
            raise SystemExit("FAIL: FracVALConfig JSON round-trip changed values")
        paths = save_bundle(a, tmp_path / "bundle", stem="sample")
        loaded = load_bundle(paths["json"])
        if not np.allclose(a.data, loaded.data, rtol=1e-8, atol=1e-8):
            raise SystemExit("FAIL: aggregate bundle round-trip changed particle data")
        if not np.allclose(a.contact_overlaps, loaded.contact_overlaps, rtol=1e-8, atol=1e-8):
            raise SystemExit("FAIL: aggregate bundle round-trip changed contact history")
        print("PASS: configuration JSON and aggregate bundle round-trips")

    info = runtime_info()
    if "extension" not in info["available_backends"]:
        raise SystemExit("FAIL: runtime diagnostics did not detect the built extension")
    print("PASS: runtime diagnostics")


if __name__ == "__main__":
    main()
