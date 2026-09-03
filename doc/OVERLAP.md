# Intended contact-overlap model

FracVAL can optionally generate partially interpenetrating primary particles at
the **intended contact used to join a particle or cluster**. This is different
from the numerical overlap tolerance `tol_ov`.

## Geometry

For primary particles with radii `Ri` and `Rj`, legacy touching contact uses
center distance

```text
d = Ri + Rj
```

For intended overlap fraction `epsilon`, FracVAL uses

```text
d = (Ri + Rj) * (1 - epsilon)
```

Thus `epsilon = 0.05` means a 5% reduction from the touching center distance.
The fraction is dimensionless and naturally scales with polydisperse radii.

## Modes

### None

```text
overlap_mode = 'none'
```

Preserves the legacy contact geometry. Intended-contact overlap records are
zero.

### Fixed

```text
overlap_mode     = 'fixed'
overlap_fraction = 0.05
```

Every intended joining contact uses the same overlap fraction.

### Statistical

```text
overlap_mode = 'statistical'
overlap_mean = 0.05
overlap_std  = 0.02
overlap_max  = 0.12
```

Each intended joining contact independently samples a normal distribution
centered at `overlap_mean` with standard deviation `overlap_std`. Samples below
zero or above `overlap_max` are rejected and redrawn, so the realized
statistics are those of a truncated/bounded distribution and need not equal the
unbounded normal parameters exactly.

With a fixed FracVAL random seed, the sampled contact history is reproducible
for the same compiler/runtime/backend build.

## Collision protection

The configured overlap is allowed only for the selected particle pair that
forms the intended PCA or CCA joining contact. All other newly introduced pair
intersections remain subject to `tol_ov`, normally `1e-6`.

This is deliberate: increasing intended contact overlap does not globally turn
off collision detection.

## Contact history

Each successful aggregate writes a sidecar such as

```text
N_00000100_Agg_00000001.contacts.csv
```

with

```text
contact_index,overlap_fraction
1,0.0471
2,0.0618
...
```

A completed tree-like `N`-particle aggregate normally has `N-1` intended
contacts. The Python `Aggregate` object exposes the same data through
`contact_overlaps`, plus `mean_contact_overlap`, `std_contact_overlap`, and
`max_contact_overlap`.

The current sidecar identifies contacts by **construction order**, not by a
persistent pair of final particle IDs. The legacy algorithm reorders particles
and clusters during construction, so persistent pair-ID tracking would require
a separate identity-propagation refactor.

## Scientific caveat

Contact overlap changes particle-center geometry and can therefore change
measured quantities such as radius of gyration and other morphology metrics.
Treat overlap settings as part of the physical model and record them with the
aggregate. Large overlap fractions can also make some requested FracVAL
configurations harder to construct and can increase PCA/CCA restart rates.
