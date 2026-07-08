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

def test_emibd9_roundtrip(tmp_path, tiny_vcf, tiny_meta):
    import shutil, csv
    from pathlib import Path
    if not (Path.home() / "programs" / "EM_IBD_P").exists():
        import pytest; pytest.skip("EM_IBD_P not available")
    shutil.copy(tiny_vcf, tmp_path / "in.vcf"); shutil.copy(tiny_meta, tmp_path / "in.csv")
    rbridge.call_gl("gl.read.vcf", {"vcf": str(tmp_path/"in.vcf"), "metafile": str(tmp_path/"in.csv"), "out": "gl.rds"}, tmp_path)
    out = rbridge.call_gl("gl.run.EMIBD9",
        {"rds": str(tmp_path/"gl.rds"), "emibd9_path": str(Path.home()/"programs"), "iseed": 42, "inbreed": False},
        tmp_path)
    assert out["outputs"] == ["relatedness.csv"]
    with open(tmp_path/"relatedness.csv") as fh:
        rows = list(csv.reader(fh))
    assert len(rows) - 1 == 12  # 12 data rows (+ header)
