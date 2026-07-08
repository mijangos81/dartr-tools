import stat, textwrap
from pathlib import Path
from dartr_tools.tools import relatedness

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
