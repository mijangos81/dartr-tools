import stat, pytest
from pathlib import Path
from dartr_tools.tools import relatedness
from dartr_tools import sandbox

def test_relatedness_local(monkeypatch, tmp_path):
    prog = tmp_path / "prog"; prog.mkdir()
    b = prog / "EM_IBD_P"
    b.write_text("#!/bin/sh\n: > relatedness.out\necho done\n")
    b.chmod(b.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(prog))
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path / "work"))
    wd = tmp_path / "work" / "s"; wd.mkdir(parents=True)
    for ext in ("bed", "bim", "fam"):
        (wd / f"in.{ext}").write_text("x\n")
    out = relatedness.run_relatedness("s", "in")
    assert (wd / "relatedness.out").is_file()

def test_relatedness_rejects_path_escape(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path / "work"))
    # "../evil" contains a path separator, so it's now rejected eagerly by the
    # bare-name guard (ValueError) before it would otherwise reach
    # resolve_input's SandboxError.
    with pytest.raises(ValueError):
        relatedness.run_relatedness("s", "../evil")

def test_relatedness_rejects_plink_prefix_with_separator(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path / "work"))
    with pytest.raises(ValueError, match="bare name"):
        relatedness.run_relatedness("s", "sub/in")
