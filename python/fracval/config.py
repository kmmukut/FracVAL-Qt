"""Configuration objects for FracVAL aggregate generation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Mapping


_OVERLAP_MODE_CODES = {
    "none": 0,
    "fixed": 1,
    "statistical": 2,
    "normal": 2,
}


@dataclass(frozen=True, slots=True)
class FracVALConfig:
    """Runtime parameters for one FracVAL aggregate.

    ``seed=None`` asks Python to choose and report a fresh seed. Passing an
    integer makes a run reproducible with the same compiler/backend build.

    Intended particle overlap is applied only to the selected contact used to
    join a monomer/cluster. Unrelated particle pairs still use ``tol_ov``.
    ``overlap_mode='statistical'`` samples a normal distribution bounded to
    ``[0, overlap_max]`` independently for each intended contact.
    """

    n: int = 100
    df: float = 1.79
    kf: float = 1.40
    rp_g: float = 15.0
    rp_gstd: float = 1.0
    ext_case: int = 0
    nsubcl_perc: float = 0.10
    tol_ov: float = 1.0e-6
    seed: int | None = None
    max_attempts: int = 250

    overlap_mode: str = "none"
    overlap_fraction: float = 0.0
    overlap_mean: float = 0.05
    overlap_std: float = 0.02
    overlap_max: float = 0.12

    @property
    def overlap_mode_code(self) -> int:
        try:
            return _OVERLAP_MODE_CODES[self.overlap_mode.strip().lower()]
        except KeyError as exc:
            raise ValueError("overlap_mode must be 'none', 'fixed', or 'statistical'") from exc

    def validate(self) -> "FracVALConfig":
        if self.n < 5:
            raise ValueError("n must be at least 5")
        if self.df <= 0:
            raise ValueError("df must be > 0")
        if self.kf <= 0:
            raise ValueError("kf must be > 0")
        if self.rp_g <= 0:
            raise ValueError("rp_g must be > 0")
        if self.rp_gstd < 1:
            raise ValueError("rp_gstd must be >= 1; use 1.0 for monodisperse particles")
        if self.ext_case not in (0, 1):
            raise ValueError("ext_case must be 0 or 1")
        if not (0 < self.nsubcl_perc <= 1):
            raise ValueError("nsubcl_perc must be in (0, 1]")
        if self.tol_ov <= 0:
            raise ValueError("tol_ov must be > 0")
        if self.seed is not None and not (0 <= self.seed <= 2_000_000_000):
            raise ValueError("seed must be between 0 and 2,000,000,000")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        mode = self.overlap_mode.strip().lower()
        if mode not in _OVERLAP_MODE_CODES:
            raise ValueError("overlap_mode must be 'none', 'fixed', or 'statistical'")
        if not (0 <= self.overlap_fraction < 0.95):
            raise ValueError("overlap_fraction must be in [0, 0.95)")
        if not (0 <= self.overlap_mean < 0.95):
            raise ValueError("overlap_mean must be in [0, 0.95)")
        if self.overlap_std < 0:
            raise ValueError("overlap_std must be >= 0")
        if not (0 < self.overlap_max < 0.95):
            raise ValueError("overlap_max must be in (0, 0.95)")
        if mode in ("statistical", "normal") and self.overlap_mean > self.overlap_max:
            raise ValueError("overlap_mean must not exceed overlap_max in statistical mode")
        return self


    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary of all generation settings."""
        return asdict(self)

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> "FracVALConfig":
        """Create and validate a configuration from a mapping."""
        return cls(**dict(values)).validate()

    def save_json(self, path: str | Path) -> Path:
        """Write this configuration as human-readable JSON and return the path."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return out

    @classmethod
    def load_json(cls, path: str | Path) -> "FracVALConfig":
        """Load a configuration from JSON. GUI parameter files are also accepted."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "config" in raw:
            raw = raw["config"]
        if not isinstance(raw, dict):
            raise ValueError("configuration JSON must contain an object")
        return cls.from_dict(raw)

    def with_updates(self, **changes: Any) -> "FracVALConfig":
        """Return a validated copy with selected fields replaced."""
        return replace(self, **changes).validate()

    def with_seed(self, seed: int) -> "FracVALConfig":
        return replace(self, seed=int(seed))
