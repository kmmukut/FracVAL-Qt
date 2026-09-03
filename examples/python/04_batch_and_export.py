"""Generate a deterministic batch and save each aggregate as a bundle."""
from pathlib import Path

from fracval import FracVALConfig, iter_generate_batch, save_bundle

output = Path("example_output/batch")
config = FracVALConfig(n=100, df=1.79, kf=1.40, seed=20260902)

for index, aggregate in enumerate(iter_generate_batch(10, config), start=1):
    stem = f"aggregate_{index:04d}_seed_{aggregate.seed}"
    save_bundle(aggregate, output, stem=stem)
    print(index, aggregate.seed, aggregate.radius_of_gyration)
