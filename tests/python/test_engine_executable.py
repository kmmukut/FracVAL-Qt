from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from fracval import FracVALConfig, GenerationError, engine


def test_subprocess_kwargs_hide_console_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    kwargs = engine._subprocess_kwargs()
    assert kwargs == {"creationflags": 0x08000000}


def test_subprocess_kwargs_empty_on_posix(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert engine._subprocess_kwargs() == {}


def test_executable_backend_creates_output_dir_before_running(tmp_path, monkeypatch):
    fake_exe = tmp_path / "fracval"
    fake_exe.write_text("")
    fake_exe.chmod(0o755)
    seen: dict[str, bool] = {}

    def fake_run(cmd, **kwargs):
        namelist = Path(cmd[1]).read_text(encoding="utf-8")
        out_dir = namelist.split("output_dir")[1].split("'")[1]
        seen["exists"] = Path(out_dir).is_dir()
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="simulated failure")

    monkeypatch.setattr(engine.subprocess, "run", fake_run)
    with pytest.raises(GenerationError):
        engine.generate(FracVALConfig(n=10, seed=1), backend="executable", executable=fake_exe)
    assert seen["exists"] is True
