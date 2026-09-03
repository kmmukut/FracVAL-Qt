"""Python-facing FracVAL generation engine."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading

import numpy as np

from .aggregate import Aggregate
from .config import FracVALConfig
from .io import load_data

_EXTENSION_LOCK = threading.Lock()


class GenerationError(RuntimeError):
    pass


def _new_seed() -> int:
    return secrets.randbelow(2_000_000_001)


def extension_available() -> bool:
    try:
        from . import _fracval_fortran  # noqa: F401
        return True
    except ImportError:
        return False


def available_backends(executable: str | Path | None = None) -> list[str]:
    backends = []
    if extension_available():
        backends.append("extension")
    if _find_executable(executable, required=False) is not None:
        backends.append("executable")
    return backends


def _find_executable(executable: str | Path | None, *, required: bool = True) -> Path | None:
    candidates: list[Path] = []
    if executable is not None:
        candidates.append(Path(executable).expanduser())
    env = os.environ.get("FRACVAL_EXECUTABLE")
    if env:
        candidates.append(Path(env).expanduser())
    # Source-tree fallback: python/fracval/engine.py -> project root.
    root = Path(__file__).resolve().parents[2]
    candidates.extend((root / "build" / "fracval", root / "build" / "fracval.exe"))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    if required:
        raise GenerationError(
            "FracVAL executable not found. Run 'make' or 'make python-ext', "
            "or set FRACVAL_EXECUTABLE."
        )
    return None


def _resolved(config: FracVALConfig) -> FracVALConfig:
    config.validate()
    return config if config.seed is not None else replace(config, seed=_new_seed())


def generate(
    config: FracVALConfig | None = None,
    *,
    backend: str = "auto",
    executable: str | Path | None = None,
) -> Aggregate:
    """Generate one aggregate.

    ``backend='auto'`` prefers the in-memory F2PY extension and falls back to
    the standalone Fortran executable.
    """
    cfg = _resolved(config or FracVALConfig())
    selected = backend.lower()
    if selected == "auto":
        selected = "extension" if extension_available() else "executable"
    if selected == "extension":
        return _generate_extension(cfg)
    if selected == "executable":
        return _generate_executable(cfg, executable)
    raise ValueError("backend must be 'auto', 'extension', or 'executable'")


def iter_generate_batch(
    count: int,
    config: FracVALConfig | None = None,
    *,
    backend: str = "auto",
    executable: str | Path | None = None,
) -> Iterator[Aggregate]:
    """Yield aggregates one at a time using deterministic per-aggregate seeds.

    This streaming form is useful for desktop applications and long parameter
    studies because callers can update progress or stop between aggregates.
    """
    if count < 1:
        raise ValueError("count must be at least 1")
    base = _resolved(config or FracVALConfig())
    rng = np.random.default_rng(base.seed)
    seeds = rng.integers(0, 2_000_000_001, size=count, dtype=np.int64)
    for seed in seeds:
        yield generate(
            replace(base, seed=int(seed)),
            backend=backend,
            executable=executable,
        )


def generate_batch(
    count: int,
    config: FracVALConfig | None = None,
    *,
    backend: str = "auto",
    executable: str | Path | None = None,
) -> list[Aggregate]:
    """Generate ``count`` aggregates with deterministic per-aggregate seeds."""
    return list(
        iter_generate_batch(
            count, config, backend=backend, executable=executable
        )
    )


def _generate_extension(cfg: FracVALConfig) -> Aggregate:
    try:
        from . import _fracval_fortran
    except ImportError as exc:
        raise GenerationError("Fortran Python extension is not built. Run 'make python-ext'.") from exc

    # The legacy Fortran numerical core uses module-global arrays/state.
    # Serialize calls so multi-threaded GUI sessions cannot corrupt that state.
    with _EXTENSION_LOCK:
        x, y, z, radius, contact_overlaps, n_contacts, status, attempts = _fracval_fortran.fracval_generate(
            cfg.n, cfg.df, cfg.kf, cfg.rp_g, cfg.rp_gstd, cfg.ext_case,
            cfg.nsubcl_perc, cfg.tol_ov, cfg.seed, cfg.max_attempts,
            cfg.overlap_mode_code, cfg.overlap_fraction, cfg.overlap_mean,
            cfg.overlap_std, cfg.overlap_max,
        )
    if status == 1:
        raise GenerationError("Fortran wrapper rejected the configuration")
    if status == 2:
        raise GenerationError(f"FracVAL failed to build an aggregate in {attempts} attempts")
    if status != 0:
        raise GenerationError(f"unknown Fortran status code {status}")
    return Aggregate(
        x, y, z, radius, cfg, int(cfg.seed), int(attempts), "extension",
        contact_overlaps=np.asarray(contact_overlaps[: int(n_contacts)], dtype=float),
    )


def _namelist(cfg: FracVALConfig, output_dir: Path) -> str:
    return f"""&fracval
    N                   = {cfg.n}
    Df                  = {cfg.df:.12g}
    kf                  = {cfg.kf:.12g}
    rp_g                = {cfg.rp_g:.12g}
    rp_gstd             = {cfg.rp_gstd:.12g}
    Quantity_aggregates = 1
    Ext_case            = {cfg.ext_case}
    Nsubcl_perc         = {cfg.nsubcl_perc:.12g}
    tol_ov              = {cfg.tol_ov:.12g}
    random_seed_value   = {cfg.seed}
    overlap_mode        = '{cfg.overlap_mode.strip().lower()}'
    overlap_fraction    = {cfg.overlap_fraction:.12g}
    overlap_mean        = {cfg.overlap_mean:.12g}
    overlap_std         = {cfg.overlap_std:.12g}
    overlap_max         = {cfg.overlap_max:.12g}
    output_dir          = '{output_dir.as_posix()}' 
/
"""


def _subprocess_kwargs() -> dict[str, int]:
    """Extra subprocess options: hide the console window of the executable on Windows."""
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    return {}


def _generate_executable(cfg: FracVALConfig, executable: str | Path | None) -> Aggregate:
    exe = _find_executable(executable)
    with tempfile.TemporaryDirectory(prefix="fracval-python-") as tmp:
        tmp_path = Path(tmp)
        out = tmp_path / "results"
        inp = tmp_path / "fracval.in"
        # Create the directory here so the Fortran shell-based mkdir is a no-op.
        out.mkdir(parents=True, exist_ok=True)
        inp.write_text(_namelist(cfg, out))
        try:
            completed = subprocess.run(
                [str(exe), str(inp)], text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, check=False, timeout=300,
                **_subprocess_kwargs(),
            )
        except subprocess.TimeoutExpired as exc:
            raise GenerationError("standalone FracVAL generation timed out") from exc
        if completed.returncode != 0:
            raise GenerationError("standalone FracVAL failed:\n" + completed.stdout[-4000:])
        files = sorted(out.glob("N_*_Agg_*.dat"))
        if len(files) != 1:
            raise GenerationError(f"expected one aggregate output, found {len(files)}")
        data = load_data(files[0])
        contact_path = files[0].with_suffix(".contacts.csv")
        contacts = np.empty(0, dtype=float)
        if contact_path.exists():
            contact_data = np.loadtxt(contact_path, delimiter=",", skiprows=1, ndmin=2)
            if contact_data.size:
                contacts = np.asarray(contact_data[:, 1], dtype=float)
        # The executable does not currently expose its internal restart count.
        return Aggregate(
            data[:, 0], data[:, 1], data[:, 2], data[:, 3], cfg,
            int(cfg.seed), None, "executable", contact_overlaps=contacts,
        )
