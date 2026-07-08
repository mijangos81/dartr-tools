import shutil, pytest
from pathlib import Path
from dartr_tools import rbridge

pytestmark = pytest.mark.skipif(
    shutil.which("Rscript") is None, reason="Rscript not available")

def test_rejects_unlisted_fn(tmp_path):
    with pytest.raises(ValueError):
        rbridge.call_gl("system", {}, tmp_path)

def test_read_vcf_roundtrip(tmp_path, tiny_vcf, tiny_meta):
    shutil.copy(tiny_vcf, tmp_path / "in.vcf")
    shutil.copy(tiny_meta, tmp_path / "tiny.csv")
    out = rbridge.call_gl(
        "gl.read.vcf",
        {
            "vcf": str(tmp_path / "in.vcf"),
            "out": "gl.rds",
            "metafile": str(tmp_path / "tiny.csv"),
        },
        tmp_path,
    )
    assert (tmp_path / "gl.rds").is_file()
    assert out["outputs"] == ["gl.rds"]
