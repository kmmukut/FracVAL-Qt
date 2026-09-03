from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from fracval import FracVALConfig, ViewerAppearance, generate, plot_3d


def main() -> None:
    agg = generate(FracVALConfig(n=25, seed=24680), backend="extension")

    appearance = ViewerAppearance(
        particle_color="#CC5500",
        opacity=0.72,
        shininess=0.80,
        background_color="#F5F5F5",
        show_axes=False,
        show_title=False,
    )
    fig = plot_3d(agg, mode="spheres", sphere_resolution=7, appearance=appearance)
    if not fig.data:
        raise SystemExit("FAIL: Plotly figure contains no traces")
    mesh = fig.data[0]
    if mesh.color != "#CC5500" or abs(mesh.opacity - 0.72) > 1e-12:
        raise SystemExit("FAIL: particle color/opacity controls were not applied")
    if abs(mesh.lighting.specular - 1.60) > 1e-12:
        raise SystemExit("FAIL: sphere shininess control was not applied")
    if fig.layout.scene.xaxis.visible is not False:
        raise SystemExit("FAIL: XYZ axes should be hidden by default/appearance setting")
    if fig.layout.scene.bgcolor != "#F5F5F5":
        raise SystemExit("FAIL: viewer background control was not applied")

    radius_view = ViewerAppearance(
        color_mode="radius",
        colorscale="Plasma",
        show_colorbar=True,
        show_axes=True,
    )
    fig_centers = plot_3d(agg, mode="centers", appearance=radius_view)
    if fig_centers.data[0].marker.showscale is not True:
        raise SystemExit("FAIL: radius legend was not enabled")
    if fig_centers.layout.scene.xaxis.visible is not True:
        raise SystemExit("FAIL: XYZ axes toggle was not applied")

    out = ROOT / "build" / "python_api_preview.html"
    fig.write_html(out, include_plotlyjs=True, full_html=True)
    print(f"PASS: appearance controls and interactive Plotly preview verified: {out}")


if __name__ == "__main__":
    main()
