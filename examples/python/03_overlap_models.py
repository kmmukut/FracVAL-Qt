"""Compare the intended-contact overlap modes."""
from fracval import FracVALConfig, generate

base = FracVALConfig(n=50, seed=24680, max_attempts=500)

cases = {
    "none": base.with_updates(overlap_mode="none"),
    "fixed_5_percent": base.with_updates(
        overlap_mode="fixed", overlap_fraction=0.05
    ),
    "statistical": base.with_updates(
        overlap_mode="statistical",
        overlap_mean=0.05,
        overlap_std=0.02,
        overlap_max=0.12,
    ),
}

for name, config in cases.items():
    aggregate = generate(config)
    print(
        f"{name:16s} contacts={aggregate.contact_count:3d} "
        f"mean={100*aggregate.mean_contact_overlap:6.3f}% "
        f"std={100*aggregate.std_contact_overlap:6.3f}% "
        f"max={100*aggregate.max_contact_overlap:6.3f}%"
    )
