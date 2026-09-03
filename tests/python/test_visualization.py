from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from fracval import FracVALConfig, ViewerAppearance, generate, plot_3d
from fracval.engine import extension_available


@pytest.fixture(scope="module")
def aggregate():
    if not extension_available():
        pytest.skip("F2PY extension not built (run: python tools/build.py ext)")
    return generate(FracVALConfig(n=25, seed=24680), backend="extension")


def test_sphere_appearance_controls(aggregate):
    appearance = ViewerAppearance(
        particle_color="#CC5500", opacity=0.72, shininess=0.80,
        background_color="#F5F5F5", show_axes=False, show_title=False,
    )
    fig = plot_3d(aggregate, mode="spheres", sphere_resolution=7, appearance=appearance)
    assert fig.data, "Plotly figure contains no traces"
    mesh = fig.data[0]
    assert mesh.color == "#CC5500" and abs(mesh.opacity - 0.72) <= 1e-12
    assert abs(mesh.lighting.specular - 1.60) <= 1e-12
    assert fig.layout.scene.xaxis.visible is False
    assert fig.layout.scene.bgcolor == "#F5F5F5"


def test_center_mode_radius_legend_and_axes(aggregate):
    radius_view = ViewerAppearance(color_mode="radius", colorscale="Plasma", show_colorbar=True, show_axes=True)
    fig = plot_3d(aggregate, mode="centers", appearance=radius_view)
    assert fig.data[0].marker.showscale is True
    assert fig.layout.scene.xaxis.visible is True


def test_interactive_html_export(aggregate, tmp_path):
    fig = plot_3d(aggregate, mode="spheres", sphere_resolution=7)
    out = tmp_path / "python_api_preview.html"
    fig.write_html(out, include_plotlyjs=True, full_html=True)
    assert out.stat().st_size > 100_000


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
