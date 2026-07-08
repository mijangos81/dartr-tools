import shutil, pytest
from dartr_tools.tools import io, filter as flt

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")

def test_filter(monkeypatch, tmp_path, tiny_vcf):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    io.read_vcf("s", str(tiny_vcf))
    out = flt.filter_snps("s", "gl.rds", callrate=0.5, maf=0.05, out="f.rds")
    assert out["outputs"] == ["f.rds"] and (tmp_path / "s" / "f.rds").is_file()
