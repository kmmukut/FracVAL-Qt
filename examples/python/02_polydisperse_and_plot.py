"""Generate a polydisperse aggregate and display it interactively."""
from fracval import FracVALConfig, ViewerAppearance, generate, plot_3d

aggregate = generate(FracVALConfig(
    n=100,
    df=1.68,
    kf=0.98,
    rp_g=15.0,
    rp_gstd=2.0,
    seed=67890,
))

appearance = ViewerAppearance(
    color_mode="radius",
    colorscale="Viridis",
    opacity=0.95,
    shininess=0.55,
    show_axes=False,
    show_colorbar=True,
)

figure = plot_3d(aggregate, mode="spheres", appearance=appearance)
figure.show()
