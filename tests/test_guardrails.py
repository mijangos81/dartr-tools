import shutil, stat, pytest
from pathlib import Path
from dartr_tools import tools
from dartr_tools.tools import admixture, io

def test_expensive_set():
    assert {"run_admixture", "run_relatedness"} <= tools.EXPENSIVE

def test_admixture_dry_run(monkeypatch, tmp_path):
    prog = tmp_path / "prog"; prog.mkdir()
    b = prog / "admixture"; b.write_text("#!/bin/sh\nexit 0\n"); b.chmod(b.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(prog))
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path / "w"))
    wd = tmp_path / "w" / "s"; wd.mkdir(parents=True)
    for e in ("bed", "bim", "fam"):
        (wd / f"in.{e}").write_text("x\n")
    out = admixture.run_admixture("s", "in", k_min=2, k_max=2, dry_run=True)
    assert out["dry_run"] and not list(wd.glob("*.Q"))

@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")
def test_read_vcf_dry_run(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    out = io.read_vcf("s1", str(tiny_vcf), metafile=str(tiny_meta), out="gl.rds", dry_run=True)
    assert out["outputs"] == []
    assert "dry_run" in out
    wd = tmp_path / "s1"
    assert not (wd / "gl.rds").is_file()
