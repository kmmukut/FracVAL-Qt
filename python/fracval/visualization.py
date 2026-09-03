"""Interactive Plotly visualization for FracVAL aggregates."""
from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np

from .aggregate import Aggregate

_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class ViewerAppearance:
    """Appearance controls shared by the desktop viewer and Python API."""

    color_mode: str = "solid"  # "solid" or "radius"
    particle_color: str = "#4C78A8"
    colorscale: str = "Viridis"
    opacity: float = 0.96
    shininess: float = 0.55
    background_color: str = "#FFFFFF"
    show_axes: bool = False
    show_colorbar: bool = False
    show_title: bool = True

    def validate(self) -> "ViewerAppearance":
        if self.color_mode not in {"solid", "radius"}:
            raise ValueError("color_mode must be 'solid' or 'radius'")
        if not _HEX_COLOR.match(self.particle_color):
            raise ValueError("particle_color must be a hex color such as #4C78A8")
        if not _HEX_COLOR.match(self.background_color):
            raise ValueError("background_color must be a hex color such as #FFFFFF")
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError("opacity must be between 0 and 1")
        if not (0.0 <= self.shininess <= 1.0):
            raise ValueError("shininess must be between 0 and 1")
        return self


def _as_data(aggregate_or_data: Aggregate | np.ndarray) -> np.ndarray:
    if isinstance(aggregate_or_data, Aggregate):
        return aggregate_or_data.data
    data = np.asarray(aggregate_or_data, dtype=float)
    if data.ndim != 2 or data.shape[1] != 4:
        raise ValueError("data must have shape (N, 4): x, y, z, radius")
    return data


def sphere_mesh(data: np.ndarray, resolution: int = 10):
    if resolution < 5:
        raise ValueError("sphere resolution must be at least 5")

    n_lat = resolution
    n_lon = 2 * resolution
    phi = np.linspace(0.0, np.pi, n_lat)
    theta = np.linspace(0.0, 2.0 * np.pi, n_lon, endpoint=False)
    sin_phi = np.sin(phi)[:, None]
    ux = sin_phi * np.cos(theta)[None, :]
    uy = sin_phi * np.sin(theta)[None, :]
    uz = np.cos(phi)[:, None] * np.ones((1, n_lon))
    unit = np.stack((ux, uy, uz), axis=-1).reshape(-1, 3)

    nv = unit.shape[0]
    local_faces = []
    for a in range(n_lat - 1):
        for b in range(n_lon):
            bn = (b + 1) % n_lon
            v00, v01 = a * n_lon + b, a * n_lon + bn
            v10, v11 = (a + 1) * n_lon + b, (a + 1) * n_lon + bn
            local_faces.extend(((v00, v10, v11), (v00, v11, v01)))
    local_faces = np.asarray(local_faces, dtype=np.int64)

    vertices, intensity, faces = [], [], []
    for idx, (x, y, z, radius) in enumerate(data):
        vertices.append(unit * radius + np.array([x, y, z]))
        intensity.append(np.full(nv, radius))
        faces.append(local_faces + idx * nv)
    return np.vstack(vertices), np.concatenate(intensity), np.vstack(faces)


def _scene_axis(visible: bool, title: str) -> dict:
    if not visible:
        return {
            "visible": False,
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
            "showbackground": False,
        }
    return {
        "visible": True,
        "title": title,
        "showgrid": True,
        "zeroline": False,
        "showbackground": False,
    }


def plot_3d(
    aggregate_or_data: Aggregate | np.ndarray,
    *,
    mode: str = "spheres",
    sphere_resolution: int = 10,
    title: str | None = None,
    appearance: ViewerAppearance | None = None,
):
    """Return an interactive Plotly 3-D figure.

    ``mode='spheres'`` renders particle geometry. ``mode='centers'`` is much
    lighter for large aggregates and sizes markers according to particle radius.

    The default appearance is intentionally clean: axes are hidden and particles
    use one solid color. Use :class:`ViewerAppearance` to control particle color,
    opacity, shininess, background, radius coloring, axes and legend visibility.
    """
    import plotly.graph_objects as go

    appearance = (appearance or ViewerAppearance()).validate()
    data = _as_data(aggregate_or_data)
    xyz, radii = data[:, :3], data[:, 3]
    fig = go.Figure()

    show_scale = appearance.color_mode == "radius" and appearance.show_colorbar

    if mode == "spheres":
        vertices, intensity, faces = sphere_mesh(data, sphere_resolution)
        mesh_kwargs = {
            "x": vertices[:, 0],
            "y": vertices[:, 1],
            "z": vertices[:, 2],
            "i": faces[:, 0],
            "j": faces[:, 1],
            "k": faces[:, 2],
            "flatshading": False,
            "hoverinfo": "skip",
            "name": "Primary particles",
            "opacity": appearance.opacity,
            "lighting": {
                "ambient": 0.45,
                "diffuse": 0.78,
                "specular": 2.0 * appearance.shininess,
                "roughness": max(0.02, 1.0 - 0.92 * appearance.shininess),
                "fresnel": 0.15 + 0.60 * appearance.shininess,
            },
            "lightposition": {"x": 900, "y": 1200, "z": 1000},
        }
        if appearance.color_mode == "radius":
            mesh_kwargs.update(
                intensity=intensity,
                colorscale=appearance.colorscale,
                showscale=show_scale,
                colorbar={"title": "Radius"},
            )
        else:
            mesh_kwargs.update(color=appearance.particle_color, showscale=False)
        fig.add_trace(go.Mesh3d(**mesh_kwargs))

        # Nearly transparent center markers preserve useful per-particle hover
        # information without visually cluttering the rendered spheres.
        fig.add_trace(go.Scatter3d(
            x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2], mode="markers",
            marker={"size": 3, "opacity": 0.015},
            customdata=np.column_stack((np.arange(1, len(data) + 1), radii)),
            hovertemplate=("Particle %{customdata[0]:.0f}<br>x=%{x:.4g}<br>"
                           "y=%{y:.4g}<br>z=%{z:.4g}<br>"
                           "radius=%{customdata[1]:.4g}<extra></extra>"),
            showlegend=False,
        ))
    elif mode == "centers":
        rmin, rmax = float(radii.min()), float(radii.max())
        if np.isclose(rmin, rmax):
            sizes = np.full_like(radii, 9.0)
        else:
            sizes = 5.0 + 13.0 * (radii - rmin) / (rmax - rmin)
        marker = {
            "size": sizes,
            "opacity": appearance.opacity,
            "showscale": show_scale,
        }
        if appearance.color_mode == "radius":
            marker.update(
                color=radii,
                colorscale=appearance.colorscale,
                colorbar={"title": "Radius"},
            )
        else:
            marker.update(color=appearance.particle_color)
        fig.add_trace(go.Scatter3d(
            x=xyz[:, 0], y=xyz[:, 1], z=xyz[:, 2], mode="markers",
            marker=marker,
            customdata=np.column_stack((np.arange(1, len(data) + 1), radii)),
            hovertemplate=("Particle %{customdata[0]:.0f}<br>x=%{x:.4g}<br>"
                           "y=%{y:.4g}<br>z=%{z:.4g}<br>"
                           "radius=%{customdata[1]:.4g}<extra></extra>"),
            name="Particle centers",
        ))
    else:
        raise ValueError("mode must be 'spheres' or 'centers'")

    default_title = title or f"FracVAL aggregate · {len(data)} primary particles"
    fig.update_layout(
        title=default_title if appearance.show_title else None,
        scene={
            "xaxis": _scene_axis(appearance.show_axes, "x"),
            "yaxis": _scene_axis(appearance.show_axes, "y"),
            "zaxis": _scene_axis(appearance.show_axes, "z"),
            "aspectmode": "data",
            "bgcolor": appearance.background_color,
        },
        paper_bgcolor=appearance.background_color,
        plot_bgcolor=appearance.background_color,
        margin={"l": 0, "r": 0, "b": 0, "t": 45 if appearance.show_title else 0},
        showlegend=False,
    )
    return fig


def plot_static(aggregate_or_data: Aggregate | np.ndarray, *, sphere_resolution: int = 16):
    """Return a static Matplotlib 3-D figure with particle spheres."""
    import matplotlib.pyplot as plt
    from matplotlib import cm, colors

    data = _as_data(aggregate_or_data)
    xyz, radii = data[:, :3], data[:, 3]
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")

    u = np.linspace(0, 2 * np.pi, 2 * sphere_resolution)
    v = np.linspace(0, np.pi, sphere_resolution)
    unit_x = np.outer(np.cos(u), np.sin(v))
    unit_y = np.outer(np.sin(u), np.sin(v))
    unit_z = np.outer(np.ones_like(u), np.cos(v))

    rmin, rmax = float(radii.min()), float(radii.max())
    norm = colors.Normalize(vmin=rmin * 0.99, vmax=rmax * 1.01) if np.isclose(rmin, rmax) else colors.Normalize(vmin=rmin, vmax=rmax)
    cmap = cm.viridis

    for (x, y, z), radius in zip(xyz, radii):
        ax.plot_surface(x + radius * unit_x, y + radius * unit_y, z + radius * unit_z,
                        color=cmap(norm(radius)), linewidth=0, antialiased=True, shade=True)

    mins = np.min(xyz - radii[:, None], axis=0)
    maxs = np.max(xyz + radii[:, None], axis=0)
    center = 0.5 * (mins + maxs)
    half_span = 0.5 * float(np.max(maxs - mins))
    ax.set_xlim(center[0] - half_span, center[0] + half_span)
    ax.set_ylim(center[1] - half_span, center[1] + half_span)
    ax.set_zlim(center[2] - half_span, center[2] + half_span)
    ax.set_box_aspect((1, 1, 1))
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.set_title(f"FracVAL aggregate · {len(data)} primary particles")
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, shrink=0.65, pad=0.08, label="Radius")
    fig.tight_layout()
    return fig
