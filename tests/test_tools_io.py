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

def test_convert_plink(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    wd = tmp_path / "s1"
    # First create a genlight RDS via read_vcf
    io.read_vcf("s1", str(tiny_vcf), metafile=str(tiny_meta), out="gl.rds")
    # Convert to plink format
    out = io.convert("s1", "gl.rds", "plink", "plk")
    assert out["outputs"] == ["plk.ped", "plk.map"]
    assert (wd / "plk.ped").is_file()
    assert (wd / "plk.map").is_file()

@pytest.mark.skipif(not (Path.home() / "programs" / "plink").exists(), reason="plink not available")
def test_convert_vcf(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(Path.home() / "programs"))
    wd = tmp_path / "s1"
    # First create a genlight RDS via read_vcf
    io.read_vcf("s1", str(tiny_vcf), metafile=str(tiny_meta), out="gl.rds")
    # Convert to VCF format
    out = io.convert("s1", "gl.rds", "vcf", "outvcf")
    assert out["outputs"] == ["outvcf.vcf"]
    assert (wd / "outvcf.vcf").is_file()

def test_convert_rejects_bad_fmt(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    # First create a genlight RDS via read_vcf
    io.read_vcf("s1", str(tiny_vcf), metafile=str(tiny_meta), out="gl.rds")
    # Attempt to convert with invalid format
    with pytest.raises(ValueError, match="fmt must be 'plink' or 'vcf'"):
        io.convert("s1", "gl.rds", "bogus", "out")
