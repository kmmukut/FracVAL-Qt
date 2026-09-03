from __future__ import annotations

import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def _force_platform(monkeypatch, build_tool, *, windows: bool, macos: bool) -> None:
    monkeypatch.setattr(build_tool, "IS_WINDOWS", windows)
    monkeypatch.setattr(build_tool, "IS_MACOS", macos)


def test_source_lists_have_fixed_order(build_tool):
    assert build_tool.CORE_SOURCES == (
        "Ctes.f90", "random.f90", "RAND_SAMPLE.f90", "a_Random_PP.f90",
        "PCA_cca.f90", "PCA_Subclusters_module.f90", "Save_results_CC.f90", "CCA_module.f90",
    )
    assert build_tool.EXE_SOURCES == build_tool.CORE_SOURCES + ("Frac_VAL_CCA.f90",)
    assert build_tool.EXT_SOURCES == build_tool.CORE_SOURCES + ("fracval_python_api.f90",)
    for name in build_tool.EXE_SOURCES + build_tool.EXT_SOURCES:
        assert (ROOT / "src" / name).is_file(), name


def test_makefile_object_list_matches_build_tool(build_tool):
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    block = makefile.split("OBJECTS :=", 1)[1].split("\n\n", 1)[0]
    objects = re.findall(r"\$\(BUILD_DIR\)/(\w+)\.o", block)
    assert objects == [Path(s).stem for s in build_tool.EXE_SOURCES]


def test_windows_rules(build_tool, monkeypatch):
    _force_platform(monkeypatch, build_tool, windows=True, macos=False)
    assert build_tool.executable_path().name == "fracval.exe"
    assert "-fPIC" not in build_tool.fortran_flags("-O2", shared=True)
    assert build_tool.fortran_flags("-O2 -g", shared=False) == ["-O2", "-g"]
    cflags = build_tool.c_flags(["/inc"], bits=64)
    assert "-DMS_WIN64" in cflags and "-fPIC" not in cflags and "-I/inc" in cflags
    assert "-DMS_WIN64" not in build_tool.c_flags([], bits=32)
    assert build_tool.executable_link_flags() == ["-static"]
    link = build_tool.extension_link_flags()
    assert link[0] == "-shared"
    assert {"-static-libgfortran", "-static-libgcc", "-static-libquadmath"} <= set(link)


def test_macos_rules(build_tool, monkeypatch):
    _force_platform(monkeypatch, build_tool, windows=False, macos=True)
    assert build_tool.executable_path().name == "fracval"
    assert "-fPIC" in build_tool.fortran_flags("-O2", shared=True)
    assert "-fPIC" not in build_tool.fortran_flags("-O2", shared=False)
    assert build_tool.extension_link_flags() == ["-bundle", "-undefined", "dynamic_lookup"]
    assert build_tool.executable_link_flags() == []
    assert build_tool.python_import_library() is None


def test_linux_rules(build_tool, monkeypatch):
    _force_platform(monkeypatch, build_tool, windows=False, macos=False)
    assert build_tool.extension_link_flags() == ["-shared"]
    assert "-fPIC" in build_tool.c_flags([], bits=64)


def test_verification_env_strips_toolchain_dirs(build_tool, tmp_path, monkeypatch):
    keep = tmp_path / "keep"
    drop = tmp_path / "drop"
    keep.mkdir()
    drop.mkdir()
    monkeypatch.setenv("PATH", os.pathsep.join([str(drop), str(keep)]))
    env = build_tool.verification_env([drop])
    entries = env["PATH"].split(os.pathsep)
    assert str(keep) in entries
    assert str(drop) not in entries
    assert env["PYTHONPATH"].endswith("python")


def test_cli_rejects_unknown_command(build_tool, capsys):
    try:
        build_tool.main(["frobnicate"])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("argparse should reject unknown commands")


def test_copy_runtime_dlls_copies_only_present_files(build_tool, tmp_path):
    src = tmp_path / "bin"
    dest = tmp_path / "pkg"
    src.mkdir()
    dest.mkdir()
    (src / "libgfortran-5.dll").write_bytes(b"x")
    (src / "libquadmath-0.dll").write_bytes(b"y")
    copied = build_tool.copy_runtime_dlls(src, dest)
    assert sorted(p.name for p in copied) == ["libgfortran-5.dll", "libquadmath-0.dll"]
    assert (dest / "libgfortran-5.dll").read_bytes() == b"x"


def test_link_flags_empty_string_yields_empty_list(build_tool):
    assert build_tool.link_flags("") == []


def test_link_flags_splits_shell_style(build_tool):
    assert build_tool.link_flags("-L/a -lb") == ["-L/a", "-lb"]


def test_cli_ldflags_default_reads_environment(build_tool, monkeypatch):
    monkeypatch.setenv("LDFLAGS", "-L/opt/conda/lib -Wl,-rpath,/opt/conda/lib")
    captured: dict[str, str] = {}

    def fake_build_executable(fc, fflags, ldflags):
        captured["ldflags"] = ldflags
        raise SystemExit(0)

    fake_compiler = build_tool.Compiler("fortran", Path("/usr/bin/gfortran"), "fake 0.0")
    fake_toolchain = type(
        "FakeToolchain", (), {"fortran": fake_compiler, "c": None, "searched": ()}
    )()
    monkeypatch.setattr(build_tool, "build_executable", fake_build_executable)
    monkeypatch.setattr(build_tool, "discover_toolchain", lambda fc=None, cc=None: fake_toolchain)

    try:
        build_tool.main(["exe"])
    except SystemExit:
        pass

    assert captured["ldflags"] == "-L/opt/conda/lib -Wl,-rpath,/opt/conda/lib"


def test_crt_search_flags_noop_off_windows(build_tool, monkeypatch):
    monkeypatch.setattr(build_tool, "IS_WINDOWS", False)

    def fail_if_called(compiler, flag):
        raise AssertionError("_compiler_query must not run off Windows")

    monkeypatch.setattr(build_tool, "_compiler_query", fail_if_called)
    assert build_tool.crt_search_flags(Path("/usr/bin/gfortran")) == []


def test_crt_search_flags_adds_b_and_l_when_unresolved(build_tool, tmp_path, monkeypatch):
    monkeypatch.setattr(build_tool, "IS_WINDOWS", True)
    libdir = tmp_path / "sysroot" / "usr" / "lib"
    libdir.mkdir(parents=True)
    (libdir / "crt2.o").write_bytes(b"x")

    def fake_query(compiler, flag):
        if flag == "-print-file-name=crt2.o":
            return "crt2.o"
        if flag == "-print-sysroot":
            return str(tmp_path / "sysroot")
        return ""

    monkeypatch.setattr(build_tool, "_compiler_query", fake_query)
    flags = build_tool.crt_search_flags(Path("x86_64-w64-mingw32-gfortran"))
    assert flags == [f"-B{libdir}", f"-L{libdir}"]


def test_crt_search_flags_noop_when_resolved(build_tool, tmp_path, monkeypatch):
    monkeypatch.setattr(build_tool, "IS_WINDOWS", True)
    resolved = tmp_path / "sysroot" / "lib" / "crt2.o"
    resolved.parent.mkdir(parents=True)
    resolved.write_bytes(b"x")

    def fake_query(compiler, flag):
        if flag == "-print-file-name=crt2.o":
            return str(resolved)
        return ""

    monkeypatch.setattr(build_tool, "_compiler_query", fake_query)
    assert build_tool.crt_search_flags(Path("x86_64-w64-mingw32-gfortran")) == []


def test_crt_search_flags_noop_when_nothing_findable(build_tool, tmp_path, monkeypatch):
    monkeypatch.setattr(build_tool, "IS_WINDOWS", True)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    def fake_query(compiler, flag):
        if flag == "-print-file-name=crt2.o":
            return "crt2.o"
        if flag == "-print-sysroot":
            return str(tmp_path / "nonexistent-sysroot")
        return ""

    monkeypatch.setattr(build_tool, "_compiler_query", fake_query)
    assert build_tool.crt_search_flags(Path("x86_64-w64-mingw32-gfortran")) == []


def test_remove_existing_extension_reports_locked_file(build_tool, tmp_path, monkeypatch):
    target = tmp_path / "_fracval_fortran.pyd"
    target.write_bytes(b"z")

    def locked(self, missing_ok=False):
        raise PermissionError("in use")

    monkeypatch.setattr(Path, "unlink", locked)
    try:
        build_tool.remove_existing_extension(target)
    except SystemExit as exc:
        assert "Close running" in str(exc)
    else:
        raise AssertionError("locked extension should produce a SystemExit with guidance")
