"""Generate one reproducible monodisperse aggregate."""
from fracval import FracVALConfig, generate, save_bundle

config = FracVALConfig(
    n=100,
    df=1.79,
    kf=1.40,
    rp_g=15.0,
    rp_gstd=1.0,
    seed=12345,
)

aggregate = generate(config)
print(f"backend: {aggregate.backend}")
print(f"seed: {aggregate.seed}")
print(f"particles: {aggregate.n}")
print(f"radius of gyration: {aggregate.radius_of_gyration:.6g}")
print(f"bounding radius: {aggregate.bounding_radius:.6g}")

written = save_bundle(aggregate, "example_output/basic", stem="monodisperse")
for kind, path in written.items():
    print(f"{kind}: {path}")
