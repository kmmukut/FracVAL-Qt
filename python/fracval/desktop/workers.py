"""Background workers used by the Qt desktop application."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ..config import FracVALConfig
from ..engine import GenerationError, iter_generate_batch


class GenerationWorker(QObject):
    """Generate a batch without blocking the Qt event loop.

    Cancellation is cooperative between aggregates. The legacy Fortran routine
    cannot safely be interrupted while one aggregate is being constructed.
    """

    aggregate_ready = Signal(int, int, object)
    progress = Signal(int, int)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal(object)

    def __init__(
        self,
        count: int,
        config: FracVALConfig,
        backend: str = "auto",
        executable: str | None = None,
    ) -> None:
        super().__init__()
        self.count = int(count)
        self.config = config
        self.backend = backend
        self.executable = executable
        self._cancel_requested = False

    @Slot()
    def cancel(self) -> None:
        self._cancel_requested = True

    @Slot()
    def run(self) -> None:
        results = []
        try:
            iterator = iter_generate_batch(
                self.count,
                self.config,
                backend=self.backend,
                executable=self.executable,
            )
            for index, aggregate in enumerate(iterator, start=1):
                if self._cancel_requested:
                    self.cancelled.emit(results)
                    return
                results.append(aggregate)
                self.aggregate_ready.emit(index, self.count, aggregate)
                self.progress.emit(index, self.count)
                if self._cancel_requested and index < self.count:
                    self.cancelled.emit(results)
                    return
        except (GenerationError, ValueError, RuntimeError) as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # Keep unexpected failures visible in the GUI.
            self.failed.emit(f"Unexpected generation error: {exc}")
            return
        self.finished.emit(results)
