import shutil, pytest
from dartr_tools.tools import io, report

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")

def _prep(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    io.read_vcf("s", str(tiny_vcf), metafile=str(tiny_meta))

def test_diversity(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    _prep(monkeypatch, tmp_path, tiny_vcf, tiny_meta)
    assert report.report_diversity("s", "gl.rds")["outputs"] == ["diversity.csv"]

def test_fst(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    _prep(monkeypatch, tmp_path, tiny_vcf, tiny_meta)
    assert report.report_fst("s", "gl.rds")["outputs"] == ["fst.rds"]

def test_pcoa(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    _prep(monkeypatch, tmp_path, tiny_vcf, tiny_meta)
    out = report.pcoa("s", "gl.rds")
    assert set(out["outputs"]) == {"pcoa.rds", "pcoa.png"}
