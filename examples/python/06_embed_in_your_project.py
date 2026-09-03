"""A minimal integration pattern for another Python application."""
from __future__ import annotations

import numpy as np

from fracval import FracVALConfig, generate


def make_particle_cloud(
    n: int,
    df: float,
    kf: float,
    *,
    seed: int | None = None,
    polydispersity: float = 1.0,
) -> np.ndarray:
    """Return an ``(N, 4)`` array: x, y, z, radius.

    This function is deliberately independent of the FracVAL GUI. It is the
    pattern to use when embedding FracVAL inside a solver, optimizer, notebook,
    database pipeline, or another desktop application.
    """
    config = FracVALConfig(
        n=n,
        df=df,
        kf=kf,
        rp_g=15.0,
        rp_gstd=polydispersity,
        seed=seed,
    )
    return generate(config).data.copy()


if __name__ == "__main__":
    cloud = make_particle_cloud(100, 1.79, 1.40, seed=12345)
    print(cloud.shape)
    print(cloud[:5])
