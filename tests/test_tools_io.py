import shutil, pytest
from pathlib import Path
from dartr_tools.tools import io

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")

def test_read_vcf(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    out = io.read_vcf("s1", str(tiny_vcf), metafile=str(tiny_meta), out="gl.rds")
    assert out["outputs"] == ["gl.rds"]
    wd = tmp_path / "s1"
    assert (wd / "gl.rds").is_file()
    assert (wd / "provenance.jsonl").is_file()
