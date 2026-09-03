"""Qt-hosted interactive Plotly aggregate viewer."""
from __future__ import annotations

from pathlib import Path
import tempfile

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

from ..aggregate import Aggregate
from ..visualization import ViewerAppearance, plot_3d


class AggregateViewer(QWebEngineView):
    """Render Plotly figures in a native Qt WebEngine widget.

    Plotly JavaScript is embedded in a temporary HTML file so visualization is
    fully offline. Loading a local file also avoids QWebEngineView.setHtml's
    data-URL size limit for Plotly's JavaScript bundle.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # Chromium may still hold the HTML file when Qt tears the widget down on
        # Windows; never let that turn into an exception at exit.
        self._tmp = tempfile.TemporaryDirectory(prefix="fracval-viewer-", ignore_cleanup_errors=True)
        self._html_path = Path(self._tmp.name) / "aggregate.html"
        self._figure = None
        self._aggregate: Aggregate | None = None
        self._mode = "spheres"
        self._sphere_resolution = 9
        self._appearance = ViewerAppearance()
        self.show_message(
            "FracVAL 3-D viewer",
            "Generate an aggregate to display and inspect it here.",
        )

    def show_message(self, title: str, message: str) -> None:
        html = f"""<!doctype html>
<html><head><meta charset='utf-8'><style>
html,body{{height:100%;margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:#f6f7f9;color:#333}} .wrap{{height:100%;display:flex;align-items:center;justify-content:center}}
.card{{max-width:560px;text-align:center;padding:32px}} h2{{font-weight:600}} p{{line-height:1.5;color:#666}}
</style></head><body><div class='wrap'><div class='card'><h2>{title}</h2><p>{message}</p></div></div></body></html>"""
        self._html_path.write_text(html, encoding="utf-8")
        self.load(QUrl.fromLocalFile(str(self._html_path)))

    def set_aggregate(
        self,
        aggregate: Aggregate,
        *,
        mode: str = "spheres",
        sphere_resolution: int = 9,
        appearance: ViewerAppearance | None = None,
    ) -> None:
        self._aggregate = aggregate
        self._mode = mode
        self._sphere_resolution = int(sphere_resolution)
        self._appearance = (appearance or self._appearance).validate()
        self._figure = plot_3d(
            aggregate,
            mode=mode,
            sphere_resolution=self._sphere_resolution,
            appearance=self._appearance,
            title=f"FracVAL aggregate · N={aggregate.n} · seed={aggregate.seed}",
        )
        self._figure.write_html(
            self._html_path,
            include_plotlyjs="inline",
            full_html=True,
            config={"scrollZoom": True, "displaylogo": False, "responsive": True},
        )
        self.load(QUrl.fromLocalFile(str(self._html_path)))

    def refresh(
        self,
        *,
        mode: str,
        sphere_resolution: int,
        appearance: ViewerAppearance | None = None,
    ) -> None:
        if self._aggregate is not None:
            self.set_aggregate(
                self._aggregate,
                mode=mode,
                sphere_resolution=sphere_resolution,
                appearance=appearance or self._appearance,
            )

    def export_html(self, path: str | Path) -> Path:
        if self._figure is None:
            raise ValueError("no aggregate is currently displayed")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._figure.write_html(
            path,
            include_plotlyjs="inline",
            full_html=True,
            config={"scrollZoom": True, "displaylogo": False, "responsive": True},
        )
        return path

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming convention)
        try:
            self._tmp.cleanup()
        finally:
            super().closeEvent(event)
