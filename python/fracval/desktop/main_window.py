"""Main window for the native FracVAL desktop application."""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import secrets
import zipfile

from PySide6.QtCore import QThread, QTimer, Qt, Slot
from PySide6.QtGui import QAction, QCloseEvent, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..aggregate import Aggregate
from ..config import FracVALConfig
from ..engine import available_backends
from ..visualization import ViewerAppearance
from .viewer import AggregateViewer
from .workers import GenerationWorker


class MainWindow(QMainWindow):
    """Native desktop controller for FracVAL generation and visualization."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FracVAL-Qt Aggregate Generator")
        self.resize(1320, 860)
        self.setMinimumSize(980, 680)

        self._aggregates: list[Aggregate] = []
        self._thread: QThread | None = None
        self._worker: GenerationWorker | None = None
        self._close_when_idle = False
        self._particle_color = ViewerAppearance().particle_color
        self._background_color = ViewerAppearance().background_color

        self._build_actions()
        self._build_ui()
        self._populate_backends()
        self._update_distribution_controls()
        self._update_seed_controls()
        self._update_overlap_controls()
        self._update_display_controls()
        self._set_running(False)

    # ---------- UI construction ----------

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        self.action_load_parameters = QAction("Load parameters…", self)
        self.action_load_parameters.triggered.connect(self.load_parameters)
        file_menu.addAction(self.action_load_parameters)

        self.action_save_parameters = QAction("Save parameters…", self)
        self.action_save_parameters.triggered.connect(self.save_parameters)
        file_menu.addAction(self.action_save_parameters)
        file_menu.addSeparator()

        self.action_save_dat = QAction("Save current aggregate as DAT…", self)
        self.action_save_dat.triggered.connect(lambda: self.save_current("dat"))
        file_menu.addAction(self.action_save_dat)

        self.action_save_csv = QAction("Save current aggregate as CSV…", self)
        self.action_save_csv.triggered.connect(lambda: self.save_current("csv"))
        file_menu.addAction(self.action_save_csv)

        self.action_save_contacts = QAction("Save contact overlaps as CSV…", self)
        self.action_save_contacts.triggered.connect(lambda: self.save_current("contacts"))
        file_menu.addAction(self.action_save_contacts)

        self.action_save_xyz = QAction("Save current aggregate as XYZ…", self)
        self.action_save_xyz.triggered.connect(lambda: self.save_current("xyz"))
        file_menu.addAction(self.action_save_xyz)

        self.action_save_json = QAction("Save current metadata as JSON…", self)
        self.action_save_json.triggered.connect(lambda: self.save_current("json"))
        file_menu.addAction(self.action_save_json)

        self.action_export_html = QAction("Export current 3-D view as HTML…", self)
        self.action_export_html.triggered.connect(self.export_view)
        file_menu.addAction(self.action_export_html)

        self.action_save_batch = QAction("Save batch as ZIP…", self)
        self.action_save_batch.triggered.connect(self.save_batch_zip)
        file_menu.addAction(self.action_save_batch)
        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("About FracVAL", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_controls())

        self.viewer = AggregateViewer()
        splitter.addWidget(self.viewer)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([350, 970])

        self.setCentralWidget(splitter)
        status = QStatusBar(self)
        self.setStatusBar(status)
        self.statusBar().showMessage("Ready")

    def _build_controls(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("FracVAL")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        subtitle = QLabel("Fortran PCA/CCA engine · native Qt controls")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        params = QGroupBox("Aggregate parameters")
        form = QFormLayout(params)

        self.n_spin = QSpinBox()
        self.n_spin.setRange(5, 100000)
        self.n_spin.setValue(100)
        self.n_spin.setSingleStep(5)
        form.addRow("Primary particles (N)", self.n_spin)

        self.df_spin = self._double_spin(0.01, 3.0, 1.79, 0.01, 4)
        form.addRow("Fractal dimension (Df)", self.df_spin)

        self.kf_spin = self._double_spin(0.001, 100.0, 1.40, 0.01, 4)
        form.addRow("Fractal prefactor (kf)", self.kf_spin)

        self.distribution_combo = QComboBox()
        self.distribution_combo.addItems(["Monodisperse", "Polydisperse"])
        self.distribution_combo.currentIndexChanged.connect(self._update_distribution_controls)
        form.addRow("Particle distribution", self.distribution_combo)

        self.rpg_spin = self._double_spin(1e-9, 1e12, 15.0, 1.0, 6)
        form.addRow("Geometric mean radius", self.rpg_spin)

        self.rpgstd_spin = self._double_spin(1.0, 100.0, 1.0, 0.05, 5)
        form.addRow("Geometric radius std. dev.", self.rpgstd_spin)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 10000)
        self.count_spin.setValue(1)
        form.addRow("Number of aggregates", self.count_spin)
        layout.addWidget(params)

        random_group = QGroupBox("Random seed")
        random_layout = QGridLayout(random_group)
        self.fixed_seed_check = QCheckBox("Use fixed base seed")
        self.fixed_seed_check.setChecked(True)
        self.fixed_seed_check.toggled.connect(self._update_seed_controls)
        random_layout.addWidget(self.fixed_seed_check, 0, 0, 1, 2)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 2_000_000_000)
        self.seed_spin.setValue(12345)
        random_layout.addWidget(QLabel("Base seed"), 1, 0)
        random_layout.addWidget(self.seed_spin, 1, 1)
        self.randomize_seed_button = QPushButton("New random seed")
        self.randomize_seed_button.clicked.connect(self.randomize_seed)
        random_layout.addWidget(self.randomize_seed_button, 2, 0, 1, 2)
        layout.addWidget(random_group)

        overlap_group = QGroupBox("Contact overlap")
        overlap_form = QFormLayout(overlap_group)
        self.overlap_mode_combo = QComboBox()
        self.overlap_mode_combo.addItem("None (touching)", "none")
        self.overlap_mode_combo.addItem("Fixed", "fixed")
        self.overlap_mode_combo.addItem("Statistical", "statistical")
        self.overlap_mode_combo.currentIndexChanged.connect(self._update_overlap_controls)
        overlap_form.addRow("Mode", self.overlap_mode_combo)

        self.overlap_fraction_spin = self._double_spin(0.0, 90.0, 5.0, 0.5, 2)
        self.overlap_fraction_spin.setSuffix(" %")
        overlap_form.addRow("Fixed overlap", self.overlap_fraction_spin)

        self.overlap_mean_spin = self._double_spin(0.0, 90.0, 5.0, 0.5, 2)
        self.overlap_mean_spin.setSuffix(" %")
        overlap_form.addRow("Mean overlap", self.overlap_mean_spin)

        self.overlap_std_spin = self._double_spin(0.0, 45.0, 2.0, 0.25, 2)
        self.overlap_std_spin.setSuffix(" %")
        overlap_form.addRow("Std. deviation", self.overlap_std_spin)

        self.overlap_max_spin = self._double_spin(0.01, 90.0, 12.0, 0.5, 2)
        self.overlap_max_spin.setSuffix(" %")
        overlap_form.addRow("Maximum overlap", self.overlap_max_spin)

        overlap_note = QLabel(
            "Overlap is applied only to the intended joining contact. "
            "Other particle pairs still use the strict numerical tolerance below."
        )
        overlap_note.setWordWrap(True)
        overlap_note.setStyleSheet("color: #666; font-size: 11px;")
        overlap_form.addRow(overlap_note)
        layout.addWidget(overlap_group)

        advanced = QGroupBox("Advanced")
        advanced.setCheckable(True)
        advanced.setChecked(False)
        advanced_form = QFormLayout(advanced)
        self.ext_case_combo = QComboBox()
        self.ext_case_combo.addItems(["0", "1"])
        advanced_form.addRow("Extreme-case mode", self.ext_case_combo)
        self.nsubcl_spin = self._double_spin(0.001, 1.0, 0.10, 0.01, 4)
        advanced_form.addRow("Sub-cluster fraction", self.nsubcl_spin)
        self.tol_spin = self._double_spin(1e-12, 1.0, 1e-6, 1e-6, 10)
        self.tol_spin.setDecimals(12)
        advanced_form.addRow("Unintended-overlap tolerance", self.tol_spin)
        self.max_attempts_spin = QSpinBox()
        self.max_attempts_spin.setRange(1, 100000)
        self.max_attempts_spin.setValue(250)
        advanced_form.addRow("Max attempts", self.max_attempts_spin)
        self.backend_combo = QComboBox()
        advanced_form.addRow("Backend", self.backend_combo)
        layout.addWidget(advanced)

        buttons = QHBoxLayout()
        self.generate_button = QPushButton("Generate")
        self.generate_button.setDefault(True)
        self.generate_button.clicked.connect(self.start_generation)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_generation)
        buttons.addWidget(self.generate_button, 2)
        buttons.addWidget(self.cancel_button, 1)
        layout.addLayout(buttons)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        display = QGroupBox("Display")
        display_form = QFormLayout(display)
        self.aggregate_combo = QComboBox()
        self.aggregate_combo.currentIndexChanged.connect(self._selected_aggregate_changed)
        display_form.addRow("Aggregate", self.aggregate_combo)
        self.render_combo = QComboBox()
        self.render_combo.addItems(["Spheres", "Centers"])
        self.render_combo.currentIndexChanged.connect(self._display_changed)
        display_form.addRow("3-D rendering", self.render_combo)
        self.resolution_spin = QSpinBox()
        self.resolution_spin.setRange(5, 18)
        self.resolution_spin.setValue(9)
        self.resolution_spin.valueChanged.connect(self._display_changed)
        display_form.addRow("Sphere resolution", self.resolution_spin)
        layout.addWidget(display)

        appearance = QGroupBox("Appearance")
        appearance_form = QFormLayout(appearance)

        self.color_mode_combo = QComboBox()
        self.color_mode_combo.addItem("Solid color", "solid")
        self.color_mode_combo.addItem("Color by radius", "radius")
        self.color_mode_combo.currentIndexChanged.connect(self._appearance_changed)
        appearance_form.addRow("Particle coloring", self.color_mode_combo)

        self.particle_color_button = QPushButton()
        self.particle_color_button.clicked.connect(self._choose_particle_color)
        appearance_form.addRow("Particle color", self.particle_color_button)

        self.colorscale_combo = QComboBox()
        self.colorscale_combo.addItems(["Viridis", "Plasma", "Cividis", "Turbo", "Inferno", "Magma"])
        self.colorscale_combo.currentIndexChanged.connect(self._appearance_changed)
        appearance_form.addRow("Radius color scale", self.colorscale_combo)

        self.opacity_spin = self._double_spin(0.05, 1.0, 0.96, 0.05, 2)
        self.opacity_spin.valueChanged.connect(self._appearance_changed)
        appearance_form.addRow("Opacity", self.opacity_spin)

        self.shininess_spin = self._double_spin(0.0, 1.0, 0.55, 0.05, 2)
        self.shininess_spin.valueChanged.connect(self._appearance_changed)
        appearance_form.addRow("Shininess", self.shininess_spin)

        self.background_color_button = QPushButton()
        self.background_color_button.clicked.connect(self._choose_background_color)
        appearance_form.addRow("Background", self.background_color_button)

        self.show_axes_check = QCheckBox("Show XYZ axes and grid")
        self.show_axes_check.setChecked(False)
        self.show_axes_check.toggled.connect(self._appearance_changed)
        appearance_form.addRow(self.show_axes_check)

        self.show_colorbar_check = QCheckBox("Show radius legend")
        self.show_colorbar_check.setChecked(False)
        self.show_colorbar_check.toggled.connect(self._appearance_changed)
        appearance_form.addRow(self.show_colorbar_check)

        self.show_title_check = QCheckBox("Show plot title")
        self.show_title_check.setChecked(True)
        self.show_title_check.toggled.connect(self._appearance_changed)
        appearance_form.addRow(self.show_title_check)

        self.reset_appearance_button = QPushButton("Reset appearance")
        self.reset_appearance_button.clicked.connect(self.reset_appearance)
        appearance_form.addRow(self.reset_appearance_button)
        layout.addWidget(appearance)

        self._update_color_button(self.particle_color_button, self._particle_color)
        self._update_color_button(self.background_color_button, self._background_color)

        stats = QGroupBox("Current aggregate")
        stats_form = QFormLayout(stats)
        self.stat_particles = QLabel("—")
        self.stat_seed = QLabel("—")
        self.stat_backend = QLabel("—")
        self.stat_attempts = QLabel("—")
        self.stat_mean_radius = QLabel("—")
        self.stat_contacts = QLabel("—")
        self.stat_overlap_mean = QLabel("—")
        self.stat_overlap_std = QLabel("—")
        self.stat_overlap_max = QLabel("—")
        self.stat_rg = QLabel("—")
        self.stat_bound = QLabel("—")
        stats_form.addRow("Particles", self.stat_particles)
        stats_form.addRow("Seed", self.stat_seed)
        stats_form.addRow("Backend", self.stat_backend)
        stats_form.addRow("Attempts", self.stat_attempts)
        stats_form.addRow("Mean radius", self.stat_mean_radius)
        stats_form.addRow("Intended contacts", self.stat_contacts)
        stats_form.addRow("Mean contact overlap", self.stat_overlap_mean)
        stats_form.addRow("Overlap std. dev.", self.stat_overlap_std)
        stats_form.addRow("Maximum contact overlap", self.stat_overlap_max)
        stats_form.addRow("Radius of gyration", self.stat_rg)
        stats_form.addRow("Bounding radius", self.stat_bound)
        layout.addWidget(stats)

        export_frame = QFrame()
        export_layout = QGridLayout(export_frame)
        export_layout.setContentsMargins(0, 0, 0, 0)
        self.save_dat_button = QPushButton("Save DAT")
        self.save_dat_button.clicked.connect(lambda: self.save_current("dat"))
        self.save_csv_button = QPushButton("Save CSV")
        self.save_csv_button.clicked.connect(lambda: self.save_current("csv"))
        self.save_contacts_button = QPushButton("Save overlaps CSV")
        self.save_contacts_button.clicked.connect(lambda: self.save_current("contacts"))
        self.export_html_button = QPushButton("Save 3-D HTML")
        self.export_html_button.clicked.connect(self.export_view)
        self.save_batch_button = QPushButton("Save batch ZIP")
        self.save_batch_button.clicked.connect(self.save_batch_zip)
        export_layout.addWidget(self.save_dat_button, 0, 0)
        export_layout.addWidget(self.save_csv_button, 0, 1)
        export_layout.addWidget(self.save_contacts_button, 1, 0)
        export_layout.addWidget(self.export_html_button, 1, 1)
        export_layout.addWidget(self.save_batch_button, 2, 0, 1, 2)
        layout.addWidget(export_frame)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        scroll.setMinimumWidth(320)
        scroll.setMaximumWidth(460)
        return scroll

    @staticmethod
    def _double_spin(
        minimum: float,
        maximum: float,
        value: float,
        step: float,
        decimals: int,
    ) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(minimum, maximum)
        widget.setDecimals(decimals)
        widget.setSingleStep(step)
        widget.setValue(value)
        return widget

    # ---------- parameters ----------

    def _populate_backends(self) -> None:
        self.backend_combo.clear()
        self.backend_combo.addItem("Auto", "auto")
        for backend in available_backends():
            label = "In-memory Fortran extension" if backend == "extension" else "Standalone executable"
            self.backend_combo.addItem(label, backend)

    def current_config(self) -> FracVALConfig:
        seed = self.seed_spin.value() if self.fixed_seed_check.isChecked() else None
        rp_gstd = 1.0 if self.distribution_combo.currentIndex() == 0 else self.rpgstd_spin.value()
        return FracVALConfig(
            n=self.n_spin.value(),
            df=self.df_spin.value(),
            kf=self.kf_spin.value(),
            rp_g=self.rpg_spin.value(),
            rp_gstd=rp_gstd,
            ext_case=int(self.ext_case_combo.currentText()),
            nsubcl_perc=self.nsubcl_spin.value(),
            tol_ov=self.tol_spin.value(),
            seed=seed,
            max_attempts=self.max_attempts_spin.value(),
            overlap_mode=self.overlap_mode_combo.currentData() or "none",
            overlap_fraction=self.overlap_fraction_spin.value()/100.0,
            overlap_mean=self.overlap_mean_spin.value()/100.0,
            overlap_std=self.overlap_std_spin.value()/100.0,
            overlap_max=self.overlap_max_spin.value()/100.0,
        ).validate()

    def set_config(self, config: FracVALConfig, *, count: int | None = None, backend: str | None = None) -> None:
        self.n_spin.setValue(config.n)
        self.df_spin.setValue(config.df)
        self.kf_spin.setValue(config.kf)
        self.rpg_spin.setValue(config.rp_g)
        if config.rp_gstd <= 1.0:
            self.distribution_combo.setCurrentIndex(0)
            self.rpgstd_spin.setValue(1.0)
        else:
            self.distribution_combo.setCurrentIndex(1)
            self.rpgstd_spin.setValue(config.rp_gstd)
        self.ext_case_combo.setCurrentText(str(config.ext_case))
        self.nsubcl_spin.setValue(config.nsubcl_perc)
        self.tol_spin.setValue(config.tol_ov)
        self.max_attempts_spin.setValue(config.max_attempts)
        overlap_mode = config.overlap_mode.strip().lower()
        if overlap_mode == "normal":
            overlap_mode = "statistical"
        overlap_idx = self.overlap_mode_combo.findData(overlap_mode)
        if overlap_idx >= 0:
            self.overlap_mode_combo.setCurrentIndex(overlap_idx)
        self.overlap_fraction_spin.setValue(100.0*config.overlap_fraction)
        self.overlap_mean_spin.setValue(100.0*config.overlap_mean)
        self.overlap_std_spin.setValue(100.0*config.overlap_std)
        self.overlap_max_spin.setValue(100.0*config.overlap_max)
        self.fixed_seed_check.setChecked(config.seed is not None)
        if config.seed is not None:
            self.seed_spin.setValue(config.seed)
        if count is not None:
            self.count_spin.setValue(int(count))
        if backend is not None:
            idx = self.backend_combo.findData(backend)
            if idx >= 0:
                self.backend_combo.setCurrentIndex(idx)
        self._update_distribution_controls()
        self._update_seed_controls()
        self._update_overlap_controls()

    @Slot(int)
    def _update_overlap_controls(self, _index: int = -1) -> None:
        mode = self.overlap_mode_combo.currentData() or "none"
        self.overlap_fraction_spin.setEnabled(mode == "fixed")
        statistical = mode == "statistical"
        self.overlap_mean_spin.setEnabled(statistical)
        self.overlap_std_spin.setEnabled(statistical)
        self.overlap_max_spin.setEnabled(statistical)

    @Slot()
    def randomize_seed(self) -> None:
        self.seed_spin.setValue(secrets.randbelow(2_000_000_001))

    @Slot(int)
    def _update_distribution_controls(self, _index: int = -1) -> None:
        mono = self.distribution_combo.currentIndex() == 0
        self.rpgstd_spin.setEnabled(not mono)
        if mono:
            self.rpgstd_spin.setValue(1.0)

    @Slot(bool)
    def _update_seed_controls(self, _checked: bool = False) -> None:
        enabled = self.fixed_seed_check.isChecked()
        self.seed_spin.setEnabled(enabled)
        self.randomize_seed_button.setEnabled(enabled)

    # ---------- generation ----------

    @Slot()
    def start_generation(self) -> None:
        if self._thread is not None:
            return
        try:
            config = self.current_config()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid parameters", str(exc))
            return

        backend = self.backend_combo.currentData() or "auto"
        count = self.count_spin.value()
        if backend == "auto" and not available_backends():
            QMessageBox.critical(
                self,
                "No FracVAL backend",
                "No generator backend is available. Build the project with 'make' "
                "or build the in-memory extension with 'make python-ext'.",
            )
            return

        self._aggregates = []
        self.aggregate_combo.clear()
        self.progress.setRange(0, count)
        self.progress.setValue(0)
        self._set_running(True)
        self.statusBar().showMessage(f"Generating 0/{count}…")

        thread = QThread(self)
        worker = GenerationWorker(count, config, backend=backend)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.aggregate_ready.connect(self._aggregate_ready)
        worker.progress.connect(self._generation_progress)
        worker.finished.connect(self._generation_finished)
        worker.cancelled.connect(self._generation_cancelled)
        worker.failed.connect(self._generation_failed)
        worker.finished.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.finished.connect(thread.quit)
        worker.cancelled.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    @Slot()
    def cancel_generation(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.cancel_button.setEnabled(False)
            self.statusBar().showMessage(
                "Cancellation requested; the current aggregate will finish before stopping."
            )

    @Slot(int, int, object)
    def _aggregate_ready(self, index: int, total: int, aggregate: Aggregate) -> None:
        self._aggregates.append(aggregate)
        self.aggregate_combo.addItem(f"Aggregate {index} · seed {aggregate.seed}")
        self.aggregate_combo.setCurrentIndex(index - 1)
        self.statusBar().showMessage(f"Generated {index}/{total}")

    @Slot(int, int)
    def _generation_progress(self, completed: int, total: int) -> None:
        self.progress.setRange(0, total)
        self.progress.setValue(completed)

    @Slot(object)
    def _generation_finished(self, aggregates: list[Aggregate]) -> None:
        self._aggregates = list(aggregates)
        self.statusBar().showMessage(f"Finished: {len(aggregates)} aggregate(s)")

    @Slot(object)
    def _generation_cancelled(self, aggregates: list[Aggregate]) -> None:
        self._aggregates = list(aggregates)
        self.statusBar().showMessage(f"Cancelled after {len(aggregates)} aggregate(s)")

    @Slot(str)
    def _generation_failed(self, message: str) -> None:
        self.statusBar().showMessage("Generation failed")
        QMessageBox.critical(self, "FracVAL generation failed", message)

    @Slot()
    def _thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._set_running(False)
        if self._close_when_idle:
            self._close_when_idle = False
            QTimer.singleShot(0, self.close)

    def _set_running(self, running: bool) -> None:
        self.generate_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self.action_load_parameters.setEnabled(not running)
        self.action_save_parameters.setEnabled(not running)
        if not running and self.progress.maximum() == 1 and not self._aggregates:
            self.progress.setValue(0)
        self._update_export_controls()

    # ---------- selection / display ----------

    @Slot(int)
    def _selected_aggregate_changed(self, _index: int = -1) -> None:
        idx = self.aggregate_combo.currentIndex()
        if not (0 <= idx < len(self._aggregates)):
            return
        aggregate = self._aggregates[idx]
        self._show_stats(aggregate)
        self.viewer.set_aggregate(
            aggregate,
            mode=self.render_combo.currentText().lower(),
            sphere_resolution=self.resolution_spin.value(),
            appearance=self.current_appearance(),
        )
        self._update_export_controls()

    @Slot(int)
    def _display_changed(self, _value: int = -1) -> None:
        self._update_display_controls()
        self._refresh_viewer()

    @Slot()
    @Slot(int)
    @Slot(float)
    @Slot(bool)
    def _appearance_changed(self, _value=None) -> None:
        self._update_display_controls()
        self._refresh_viewer()

    def _refresh_viewer(self) -> None:
        idx = self.aggregate_combo.currentIndex()
        if 0 <= idx < len(self._aggregates):
            self.viewer.refresh(
                mode=self.render_combo.currentText().lower(),
                sphere_resolution=self.resolution_spin.value(),
                appearance=self.current_appearance(),
            )

    def _update_display_controls(self) -> None:
        spheres = self.render_combo.currentText().lower() == "spheres"
        radius_coloring = self.color_mode_combo.currentData() == "radius" if hasattr(self, "color_mode_combo") else False
        self.resolution_spin.setEnabled(spheres)
        if hasattr(self, "shininess_spin"):
            self.shininess_spin.setEnabled(spheres)
            self.particle_color_button.setEnabled(not radius_coloring)
            self.colorscale_combo.setEnabled(radius_coloring)
            self.show_colorbar_check.setEnabled(radius_coloring)

    def current_appearance(self) -> ViewerAppearance:
        return ViewerAppearance(
            color_mode=self.color_mode_combo.currentData() or "solid",
            particle_color=self._particle_color,
            colorscale=self.colorscale_combo.currentText(),
            opacity=self.opacity_spin.value(),
            shininess=self.shininess_spin.value(),
            background_color=self._background_color,
            show_axes=self.show_axes_check.isChecked(),
            show_colorbar=self.show_colorbar_check.isChecked(),
            show_title=self.show_title_check.isChecked(),
        ).validate()

    def set_appearance(self, appearance: ViewerAppearance) -> None:
        appearance = appearance.validate()
        idx = self.color_mode_combo.findData(appearance.color_mode)
        if idx >= 0:
            self.color_mode_combo.setCurrentIndex(idx)
        self._particle_color = appearance.particle_color.upper()
        self._background_color = appearance.background_color.upper()
        self._update_color_button(self.particle_color_button, self._particle_color)
        self._update_color_button(self.background_color_button, self._background_color)
        scale_idx = self.colorscale_combo.findText(appearance.colorscale)
        if scale_idx >= 0:
            self.colorscale_combo.setCurrentIndex(scale_idx)
        self.opacity_spin.setValue(appearance.opacity)
        self.shininess_spin.setValue(appearance.shininess)
        self.show_axes_check.setChecked(appearance.show_axes)
        self.show_colorbar_check.setChecked(appearance.show_colorbar)
        self.show_title_check.setChecked(appearance.show_title)
        self._update_display_controls()

    @staticmethod
    def _update_color_button(button: QPushButton, color_hex: str) -> None:
        color = QColor(color_hex)
        luminance = 0.2126 * color.redF() + 0.7152 * color.greenF() + 0.0722 * color.blueF()
        text_color = "#000000" if luminance > 0.55 else "#FFFFFF"
        button.setText(color_hex.upper())
        button.setStyleSheet(
            f"QPushButton {{ background-color: {color_hex}; color: {text_color}; "
            "border: 1px solid #888; border-radius: 4px; padding: 4px; }}"
        )

    @Slot()
    def _choose_particle_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._particle_color), self, "Choose particle color")
        if color.isValid():
            self._particle_color = color.name().upper()
            self._update_color_button(self.particle_color_button, self._particle_color)
            self._appearance_changed()

    @Slot()
    def _choose_background_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._background_color), self, "Choose viewer background")
        if color.isValid():
            self._background_color = color.name().upper()
            self._update_color_button(self.background_color_button, self._background_color)
            self._appearance_changed()

    @Slot()
    def reset_appearance(self) -> None:
        self.set_appearance(ViewerAppearance())
        self._appearance_changed()

    def _show_stats(self, aggregate: Aggregate) -> None:
        self.stat_particles.setText(str(aggregate.n))
        self.stat_seed.setText(str(aggregate.seed))
        self.stat_backend.setText(aggregate.backend)
        self.stat_attempts.setText("—" if aggregate.attempts is None else str(aggregate.attempts))
        self.stat_mean_radius.setText(f"{aggregate.radius.mean():.6g}")
        self.stat_contacts.setText(str(aggregate.contact_count))
        self.stat_overlap_mean.setText(f"{100.0*aggregate.mean_contact_overlap:.3f} %")
        self.stat_overlap_std.setText(f"{100.0*aggregate.std_contact_overlap:.3f} %")
        self.stat_overlap_max.setText(f"{100.0*aggregate.max_contact_overlap:.3f} %")
        self.stat_rg.setText(f"{aggregate.radius_of_gyration:.6g}")
        self.stat_bound.setText(f"{aggregate.bounding_radius:.6g}")

    def _current_aggregate(self) -> Aggregate | None:
        idx = self.aggregate_combo.currentIndex()
        if 0 <= idx < len(self._aggregates):
            return self._aggregates[idx]
        return None

    def _update_export_controls(self) -> None:
        has_current = self._current_aggregate() is not None
        has_batch = bool(self._aggregates)
        for widget in (self.save_dat_button, self.save_csv_button, self.save_contacts_button, self.export_html_button):
            widget.setEnabled(has_current)
        self.save_batch_button.setEnabled(has_batch)
        for action in (
            self.action_save_dat,
            self.action_save_csv,
            self.action_save_contacts,
            self.action_save_xyz,
            self.action_save_json,
            self.action_export_html,
        ):
            action.setEnabled(has_current)
        self.action_save_batch.setEnabled(has_batch)

    # ---------- save / load ----------

    @Slot()
    def save_parameters(self) -> None:
        try:
            config = self.current_config()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid parameters", str(exc))
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save FracVAL parameters", "fracval_parameters.json", "JSON (*.json)")
        if not path:
            return
        payload = {
            "config": asdict(config),
            "count": self.count_spin.value(),
            "backend": self.backend_combo.currentData() or "auto",
            "appearance": asdict(self.current_appearance()),
        }
        Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self.statusBar().showMessage(f"Saved parameters: {path}")

    @Slot()
    def load_parameters(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load FracVAL parameters", "", "JSON (*.json);;All files (*)")
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            raw = payload.get("config", payload)
            config = FracVALConfig(**raw).validate()
            self.set_config(config, count=payload.get("count"), backend=payload.get("backend"))
            if "appearance" in payload:
                self.set_appearance(ViewerAppearance(**payload["appearance"]))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            QMessageBox.critical(self, "Could not load parameters", str(exc))
            return
        self.statusBar().showMessage(f"Loaded parameters: {path}")

    def save_current(self, fmt: str) -> None:
        aggregate = self._current_aggregate()
        if aggregate is None:
            return
        filters = {
            "dat": "FracVAL data (*.dat)",
            "csv": "CSV (*.csv)",
            "contacts": "Contact overlaps CSV (*.contacts.csv)",
            "xyz": "XYZ (*.xyz)",
            "json": "JSON (*.json)",
        }
        default = (f"aggregate_seed_{aggregate.seed}.contacts.csv" if fmt == "contacts"
                   else f"aggregate_seed_{aggregate.seed}.{fmt}")
        path, _ = QFileDialog.getSaveFileName(self, f"Save aggregate as {fmt.upper()}", default, filters[fmt])
        if not path:
            return
        saved = aggregate.save(path, fmt)
        self.statusBar().showMessage(f"Saved {saved}")

    @Slot()
    def export_view(self) -> None:
        aggregate = self._current_aggregate()
        if aggregate is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export interactive 3-D view",
            f"aggregate_seed_{aggregate.seed}.html",
            "HTML (*.html)",
        )
        if not path:
            return
        try:
            saved = self.viewer.export_html(path)
        except ValueError as exc:
            QMessageBox.warning(self, "Nothing to export", str(exc))
            return
        self.statusBar().showMessage(f"Saved interactive view: {saved}")

    @Slot()
    def save_batch_zip(self) -> None:
        if not self._aggregates:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save aggregate batch", "fracval_batch.zip", "ZIP archive (*.zip)")
        if not path:
            return
        path_obj = Path(path)
        if path_obj.suffix.lower() != ".zip":
            path_obj = path_obj.with_suffix(".zip")
        with zipfile.ZipFile(path_obj, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for index, aggregate in enumerate(self._aggregates, start=1):
                stem = f"aggregate_{index:04d}_seed_{aggregate.seed}"
                zf.writestr(stem + ".dat", aggregate.to_dat_text())
                zf.writestr(stem + ".csv", aggregate.to_csv_text())
                zf.writestr(stem + ".contacts.csv", aggregate.to_contacts_csv_text())
                zf.writestr(stem + ".json", json.dumps(aggregate.metadata(), indent=2) + "\n")
            zf.writestr(
                "batch.json",
                json.dumps(
                    {
                        "count": len(self._aggregates),
                        "aggregates": [item.metadata() for item in self._aggregates],
                    },
                    indent=2,
                ) + "\n",
            )
        self.statusBar().showMessage(f"Saved batch: {path_obj}")

    # ---------- misc ----------

    @Slot()
    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "About FracVAL",
            "FracVAL-Qt Aggregate Generator\n\n"
            "Native PySide6 desktop frontend for the existing FracVAL Fortran "
            "particle-cluster / cluster-cluster aggregation engine.\n\n"
            "The Qt application controls generation; the scientific aggregation "
            "algorithm remains in Fortran.",
        )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt naming convention)
        if self._thread is not None and self._thread.isRunning():
            answer = QMessageBox.question(
                self,
                "Generation in progress",
                "An aggregate is still being generated. Request cancellation and close after the current aggregate finishes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.No:
                event.ignore()
                return
            if self._worker is not None:
                self._worker.cancel()
            self._close_when_idle = True
            self.statusBar().showMessage(
                "Closing after the current aggregate finishes…"
            )
            event.ignore()
            return
        event.accept()
