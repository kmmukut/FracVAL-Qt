#!/usr/bin/env python3
"""Visualize a native FracVAL x y z radius file.

Plotly provides interactive 3-D sphere or center rendering. Matplotlib provides
static sphere rendering suitable for PNG/PDF export.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from fracval.io import load_data
from fracval.visualization import ViewerAppearance, plot_3d, plot_static


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("aggregate", type=Path)
    p.add_argument("--backend", choices=("plotly", "matplotlib"), default="plotly")
    p.add_argument("--mode", choices=("spheres", "centers"), default="spheres")
    p.add_argument("--sphere-resolution", type=int, default=10)
    p.add_argument("--output", type=Path, help="HTML for Plotly; image path such as PNG for Matplotlib")
    p.add_argument("--color", default="#4C78A8", help="solid particle color as #RRGGBB")
    p.add_argument("--color-by-radius", action="store_true", help="color particles by radius instead of one solid color")
    p.add_argument("--colorscale", default="Viridis", help="Plotly colorscale used with --color-by-radius")
    p.add_argument("--opacity", type=float, default=0.96)
    p.add_argument("--shininess", type=float, default=0.55, help="sphere shininess from 0 (matte) to 1 (glossy)")
    p.add_argument("--background", default="#FFFFFF", help="viewer background as #RRGGBB")
    p.add_argument("--axes", action="store_true", help="show XYZ axes/grid (hidden by default)")
    p.add_argument("--colorbar", action="store_true", help="show radius color legend")
    p.add_argument("--no-title", action="store_true", help="hide the plot title")
    args = p.parse_args()

    data = load_data(args.aggregate)
    if args.backend == "plotly":
        appearance = ViewerAppearance(
            color_mode="radius" if args.color_by_radius else "solid",
            particle_color=args.color,
            colorscale=args.colorscale,
            opacity=args.opacity,
            shininess=args.shininess,
            background_color=args.background,
            show_axes=args.axes,
            show_colorbar=args.colorbar,
            show_title=not args.no_title,
        ).validate()
        fig = plot_3d(
            data,
            mode=args.mode,
            sphere_resolution=args.sphere_resolution,
            appearance=appearance,
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            fig.write_html(args.output, include_plotlyjs=True, full_html=True)
            print(f"Wrote interactive plot: {args.output}")
        else:
            fig.show()
    else:
        fig = plot_static(data, sphere_resolution=args.sphere_resolution)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(args.output, dpi=180, bbox_inches="tight")
            print(f"Wrote static plot: {args.output}")
        else:
            import matplotlib.pyplot as plt
            plt.show()


if __name__ == "__main__":
    main()
