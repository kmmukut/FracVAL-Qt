"""Aggregate result container and derived geometric quantities."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import numpy as np

from .config import FracVALConfig


@dataclass(slots=True)
class Aggregate:
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    radius: np.ndarray
    config: FracVALConfig
    seed: int
    attempts: int | None
    backend: str
    contact_overlaps: np.ndarray | None = None

    def __post_init__(self) -> None:
        arrays = [np.asarray(v, dtype=float) for v in (self.x, self.y, self.z, self.radius)]
        if len({a.shape for a in arrays}) != 1 or arrays[0].ndim != 1:
            raise ValueError("x, y, z, and radius must be 1-D arrays with equal length")
        if len(arrays[0]) != self.config.n:
            raise ValueError("aggregate array length does not match config.n")
        if not all(np.isfinite(a).all() for a in arrays):
            raise ValueError("aggregate contains NaN or infinite values")
        if np.any(arrays[3] <= 0):
            raise ValueError("particle radii must be positive")
        self.x, self.y, self.z, self.radius = arrays

        if self.contact_overlaps is None:
            contacts = np.empty(0, dtype=float)
        else:
            contacts = np.asarray(self.contact_overlaps, dtype=float)
        if contacts.ndim != 1:
            raise ValueError("contact_overlaps must be a 1-D array")
        if not np.isfinite(contacts).all():
            raise ValueError("contact_overlaps contains NaN or infinite values")
        if np.any((contacts < 0) | (contacts >= 1)):
            raise ValueError("contact overlap fractions must be in [0, 1)")
        if len(contacts) > max(0, self.config.n - 1):
            raise ValueError("too many contact-overlap records for aggregate size")
        self.contact_overlaps = contacts

    @property
    def n(self) -> int:
        return len(self.x)

    @property
    def xyz(self) -> np.ndarray:
        return np.column_stack((self.x, self.y, self.z))

    @property
    def data(self) -> np.ndarray:
        return np.column_stack((self.x, self.y, self.z, self.radius))

    @property
    def masses(self) -> np.ndarray:
        # A common density factor cancels from all normalized geometric metrics.
        return self.radius**3

    @property
    def center_of_mass(self) -> np.ndarray:
        m = self.masses
        return np.sum(self.xyz * m[:, None], axis=0) / np.sum(m)

    @property
    def radius_of_gyration(self) -> float:
        m = self.masses
        cm = self.center_of_mass
        d2 = np.sum((self.xyz - cm) ** 2, axis=1)
        # Include the intrinsic moment of a solid sphere: 3/5 r^2.
        return float(np.sqrt(np.sum(m * (d2 + 0.6 * self.radius**2)) / np.sum(m)))

    @property
    def bounding_radius(self) -> float:
        cm = self.center_of_mass
        return float(np.max(np.linalg.norm(self.xyz - cm, axis=1) + self.radius))

    @property
    def contact_count(self) -> int:
        return int(len(self.contact_overlaps))

    @property
    def mean_contact_overlap(self) -> float:
        return float(np.mean(self.contact_overlaps)) if self.contact_count else 0.0

    @property
    def std_contact_overlap(self) -> float:
        return float(np.std(self.contact_overlaps, ddof=1)) if self.contact_count > 1 else 0.0

    @property
    def max_contact_overlap(self) -> float:
        return float(np.max(self.contact_overlaps)) if self.contact_count else 0.0

    def metadata(self) -> dict:
        return {
            "config": asdict(self.config),
            "seed": self.seed,
            "attempts": self.attempts,
            "backend": self.backend,
            "derived": {
                "center_of_mass": self.center_of_mass.tolist(),
                "radius_of_gyration": self.radius_of_gyration,
                "bounding_radius": self.bounding_radius,
                "mean_radius": float(np.mean(self.radius)),
                "geometric_mean_radius": float(np.exp(np.mean(np.log(self.radius)))),
                "contact_count": self.contact_count,
                "mean_contact_overlap": self.mean_contact_overlap,
                "std_contact_overlap": self.std_contact_overlap,
                "max_contact_overlap": self.max_contact_overlap,
            },
            "contact_overlaps": self.contact_overlaps.tolist(),
        }

    def to_dat_text(self) -> str:
        return "".join("{:.9g} {:.9g} {:.9g} {:.9g}\n".format(*row) for row in self.data)

    def to_csv_text(self) -> str:
        lines = ["x,y,z,radius\n"]
        lines.extend("{:.9g},{:.9g},{:.9g},{:.9g}\n".format(*row) for row in self.data)
        return "".join(lines)

    def to_contacts_csv_text(self) -> str:
        lines = ["contact_index,overlap_fraction\n"]
        lines.extend(f"{i},{value:.9g}\n" for i, value in enumerate(self.contact_overlaps, start=1))
        return "".join(lines)

    def to_xyz_text(self) -> str:
        # Generic XYZ-like output: one pseudo-atom per primary particle.
        lines = [f"{self.n}\n", f"FracVAL seed={self.seed} Df={self.config.df} kf={self.config.kf}\n"]
        lines.extend("P {:.9g} {:.9g} {:.9g}\n".format(x, y, z) for x, y, z in self.xyz)
        return "".join(lines)

    def save(self, path: str | Path, format: str | None = None) -> Path:
        path = Path(path)
        if format is None and path.name.lower().endswith(".contacts.csv"):
            fmt = "contacts"
        else:
            fmt = (format or path.suffix.lstrip(".") or "dat").lower()
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "dat":
            path.write_text(self.to_dat_text())
        elif fmt == "csv":
            path.write_text(self.to_csv_text())
        elif fmt in ("contacts", "contacts.csv"):
            path.write_text(self.to_contacts_csv_text())
        elif fmt == "xyz":
            path.write_text(self.to_xyz_text())
        elif fmt == "json":
            path.write_text(json.dumps(self.metadata(), indent=2) + "\n")
        else:
            raise ValueError(f"unsupported format: {fmt}")
        return path
