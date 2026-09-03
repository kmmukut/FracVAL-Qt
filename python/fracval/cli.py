"""Command-line entry points for the Python frontend."""
from __future__ import annotations

import argparse
from pathlib import Path

from .config import FracVALConfig
from .engine import generate


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fracval-python", description="Generate a FracVAL aggregate from Python")
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--df", type=float, default=1.79)
    p.add_argument("--kf", type=float, default=1.40)
    p.add_argument("--rp-g", type=float, default=15.0)
    p.add_argument("--rp-gstd", type=float, default=1.0)
    p.add_argument("--seed", type=int)
    p.add_argument("--backend", choices=("auto", "extension", "executable"), default="auto")
    p.add_argument("--overlap-mode", choices=("none", "fixed", "statistical"), default="none")
    p.add_argument("--overlap", type=float, default=0.0,
                   help="fixed intended-contact overlap fraction, e.g. 0.05 for 5%%")
    p.add_argument("--overlap-mean", type=float, default=0.05)
    p.add_argument("--overlap-std", type=float, default=0.02)
    p.add_argument("--overlap-max", type=float, default=0.12)
    p.add_argument("--output", type=Path, default=Path("aggregate.dat"))
    return p


def main() -> None:
    args = _parser().parse_args()
    cfg = FracVALConfig(
        n=args.n,
        df=args.df,
        kf=args.kf,
        rp_g=args.rp_g,
        rp_gstd=args.rp_gstd,
        seed=args.seed,
        overlap_mode=args.overlap_mode,
        overlap_fraction=args.overlap,
        overlap_mean=args.overlap_mean,
        overlap_std=args.overlap_std,
        overlap_max=args.overlap_max,
    )
    agg = generate(cfg, backend=args.backend)
    agg.save(args.output)
    meta = args.output.with_suffix(".json")
    contacts = args.output.with_suffix(".contacts.csv")
    agg.save(meta, "json")
    agg.save(contacts, "contacts")
    print(f"Wrote {args.output} ({agg.n} particles, seed={agg.seed}, backend={agg.backend})")
    print(f"Contact overlap: mean={100*agg.mean_contact_overlap:.3f}% max={100*agg.max_contact_overlap:.3f}%")
    print(f"Contacts: {contacts}")
    print(f"Metadata: {meta}")


def gui_main() -> None:
    """Backward-compatible entry point for the native Qt application."""
    from .desktop.main import main as desktop_main
    raise SystemExit(desktop_main())
