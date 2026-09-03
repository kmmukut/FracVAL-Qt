from __future__ import annotations

import shutil

from fracval import diagnostics


def test_runtime_info_reports_compilers():
    info = diagnostics.runtime_info()
    for key in ("fortran_compiler", "c_compiler"):
        assert key in info
        value = info[key]
        assert value is None or set(value) == {"path", "version"}


def test_format_mentions_compilers_and_hint_when_missing(monkeypatch):
    monkeypatch.setenv("FC", "no-such-fortran-zzz")
    monkeypatch.setenv("CC", "no-such-c-zzz")
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: None)
    text = diagnostics.format_runtime_info()
    assert "Fortran compiler" in text
    assert "C compiler" in text
    assert "not found" in text
    assert "conda install" in text
