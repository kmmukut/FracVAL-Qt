"""File I/O helpers for native FracVAL data and portable result bundles."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np

from .aggregate import Aggregate
from .config import FracVALConfig


def load_data(path: str | Path) -> np.ndarray:
    """Read a native four-column FracVAL ``.dat`` file.

    Returns an ``(N, 4)`` NumPy array with columns ``x, y, z, radius``.
    """
    path = Path(path)
    data = np.loadtxt(path, dtype=float)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.ndim != 2 or data.shape[1] != 4:
        raise ValueError(f"expected four columns (x y z radius), got shape {data.shape}")
    if not np.isfinite(data).all():
        raise ValueError("aggregate contains NaN or infinite values")
    if np.any(data[:, 3] <= 0):
        raise ValueError("all particle radii must be positive")
    return data


def _load_contacts(path: Path) -> np.ndarray:
    if not path.exists():
        return np.empty(0, dtype=float)
    rows = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    if rows.size == 0:
        return np.empty(0, dtype=float)
    if rows.shape[1] < 2:
        raise ValueError(f"invalid contact-overlap file: {path}")
    return np.asarray(rows[:, 1], dtype=float)


def save_bundle(
    aggregate: Aggregate,
    directory: str | Path,
    *,
    stem: str | None = None,
    formats: Iterable[str] = ("dat", "csv", "contacts", "json"),
) -> dict[str, Path]:
    """Save one aggregate as a self-describing set of files.

    Parameters
    ----------
    aggregate:
        The generated :class:`~fracval.Aggregate`.
    directory:
        Destination directory, created when necessary.
    stem:
        Common filename stem. By default ``aggregate_seed_<seed>``.
    formats:
        Any of ``dat``, ``csv``, ``contacts``, ``xyz`` and ``json``.

    Returns
    -------
    dict
        Mapping from format name to written path.
    """
    out_dir = Path(directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = stem or f"aggregate_seed_{aggregate.seed}"
    suffixes = {
        "dat": ".dat",
        "csv": ".csv",
        "contacts": ".contacts.csv",
        "xyz": ".xyz",
        "json": ".json",
    }
    written: dict[str, Path] = {}
    for fmt in formats:
        key = fmt.lower()
        if key not in suffixes:
            raise ValueError(f"unsupported bundle format: {fmt}")
        path = out_dir / (base + suffixes[key])
        aggregate.save(path, key)
        written[key] = path
    return written


def load_bundle(metadata_path: str | Path) -> Aggregate:
    """Load an aggregate previously saved by :func:`save_bundle`.

    ``metadata_path`` is the bundle's ``.json`` metadata file. The matching
    ``.dat`` and optional ``.contacts.csv`` files are read from the same
    directory using the same filename stem.
    """
    meta_path = Path(metadata_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if not isinstance(meta, dict) or "config" not in meta:
        raise ValueError("aggregate metadata JSON must contain a 'config' object")

    cfg = FracVALConfig.from_dict(meta["config"])
    stem = meta_path.name[:-5] if meta_path.name.lower().endswith(".json") else meta_path.stem
    data_path = meta_path.with_name(stem + ".dat")
    contacts_path = meta_path.with_name(stem + ".contacts.csv")
    if not data_path.exists():
        raise FileNotFoundError(f"bundle data file not found: {data_path}")

    data = load_data(data_path)
    if len(data) != cfg.n:
        raise ValueError(f"bundle contains {len(data)} particles but metadata says n={cfg.n}")

    contacts = _load_contacts(contacts_path)
    return Aggregate(
        data[:, 0],
        data[:, 1],
        data[:, 2],
        data[:, 3],
        cfg,
        int(meta.get("seed", cfg.seed if cfg.seed is not None else 0)),
        meta.get("attempts"),
        str(meta.get("backend", "file")),
        contact_overlaps=contacts,
    )
