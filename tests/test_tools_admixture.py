import os, stat, textwrap, pytest
from pathlib import Path
from dartr_tools.tools import admixture

def _stub(progdir: Path):
    b = progdir / "admixture"
    b.write_text(textwrap.dedent("""\
        #!/bin/sh
        # emit fake CV line + Q/P files named like admixture does
        K=$3
        echo "CV error (K=$K): 0.4$K"
        base=$(basename "$2" .bed)
        : > "${base}.${K}.Q"; : > "${base}.${K}.P"
    """))
    b.chmod(b.stat().st_mode | stat.S_IEXEC)

def test_admixture_local(monkeypatch, tmp_path):
    prog = tmp_path / "prog"; prog.mkdir(); _stub(prog)
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(prog))
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path / "work"))
    wd = tmp_path / "work" / "s"; wd.mkdir(parents=True)
    for ext in ("bed", "bim", "fam"):
        (wd / f"in.{ext}").write_text("snp1\nsnp2\n")   # 2-line .bim => 2 SNPs
    out = admixture.run_admixture("s", plink="in", k_min=2, k_max=3)
    assert set(out["cv"]) == {2, 3} and out["cv"][2] == 0.42
