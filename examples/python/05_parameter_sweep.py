"""Small parameter sweep suitable as a template for a research workflow."""
import csv
from pathlib import Path

from fracval import FracVALConfig, generate

rows = []
base_seed = 10000
for i, df in enumerate((1.6, 1.8, 2.0)):
    for j, kf in enumerate((0.9, 1.2, 1.5)):
        config = FracVALConfig(
            n=100,
            df=df,
            kf=kf,
            rp_g=15.0,
            rp_gstd=1.0,
            seed=base_seed + 100 * i + j,
            max_attempts=500,
        )
        aggregate = generate(config)
        rows.append({
            "df": df,
            "kf": kf,
            "seed": aggregate.seed,
            "radius_of_gyration": aggregate.radius_of_gyration,
            "bounding_radius": aggregate.bounding_radius,
            "attempts": aggregate.attempts,
        })
        print(rows[-1])

out = Path("example_output/parameter_sweep.csv")
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0])
    writer.writeheader()
    writer.writerows(rows)
print(f"wrote {out}")
