import shutil, pytest
from pathlib import Path
from dartr_tools.tools import io, ne

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")

@pytest.mark.skipif(not (Path.home()/"programs"/"Ne2-1M").exists(), reason="Ne2-1M not available")
def test_ne(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(Path.home() / "programs"))  # wherever Ne2-1M lives in the env
    io.read_vcf("s", str(tiny_vcf), metafile=str(tiny_meta))
    out = ne.estimate_ne("s", "gl.rds")
    assert out["outputs"] == ["ne.rds"]
    assert (tmp_path / "s" / "ne.rds").is_file()
