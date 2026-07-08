import shutil, csv, statistics, pytest
from pathlib import Path
from dartr_tools.tools import io, relatedness
from dartr_tools import sandbox

_HAVE = shutil.which("Rscript") is not None and (Path.home()/"programs"/"EM_IBD_P").exists()
real = pytest.mark.skipif(not _HAVE, reason="Rscript or EM_IBD_P not available")

def _cells(path):
    with open(path) as fh:
        rows = list(csv.reader(fh))
    body = rows[1:]                      # drop header
    return [[c for c in r[1:]] for r in body]   # drop rowname col

def _prep(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(Path.home()/"programs"))
    io.read_vcf("s", str(tiny_vcf), metafile=str(tiny_meta))

@real
def test_relatedness_matrix(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    _prep(monkeypatch, tmp_path, tiny_vcf, tiny_meta)
    out = relatedness.run_relatedness("s", "gl.rds")
    assert out["outputs"] == ["relatedness.csv"]
    cells = _cells(tmp_path/"s"/"relatedness.csv")
    n = len(cells)
    assert n == 12 and all(len(r) == n for r in cells)                      # square 12x12
    nums = [float(c) for r in cells for c in r if c not in ("", "NA")]
    assert nums and all(0.0 <= v <= 1.0 for v in nums)                      # r in [0,1]
    diag = [float(cells[i][i]) for i in range(n) if cells[i][i] not in ("", "NA")]
    assert abs(statistics.mean(diag) - 0.5) < 0.05                          # self ~ 0.5

@real
def test_relatedness_deterministic(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    _prep(monkeypatch, tmp_path, tiny_vcf, tiny_meta)
    relatedness.run_relatedness("s", "gl.rds")
    first = (tmp_path/"s"/"relatedness.csv").read_text()
    relatedness.run_relatedness("s", "gl.rds")            # ISeed=42 fixed
    assert (tmp_path/"s"/"relatedness.csv").read_text() == first

def test_relatedness_rejects_path_escape(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path/"work"))
    with pytest.raises(sandbox.SandboxError):
        relatedness.run_relatedness("s", "../evil.rds")
