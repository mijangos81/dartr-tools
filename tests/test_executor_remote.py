import os, pytest
from pathlib import Path
from dartr_tools import executor

def test_dry_run_builds_ssh(tmp_path):
    r = executor.run_remote(["admixture", "x.bed", "2"], remote_cwd="/mnt/local/output/s1",
                            host="luism01", stage_in=[], stage_out_dir=tmp_path, dry_run=True)
    assert "ssh" in r.stdout and "luism01" in r.stdout

@pytest.mark.skipif(os.environ.get("DARTR_TEST_LUISM01") != "1", reason="luism01 not available")
def test_real_roundtrip(tmp_path):
    (tmp_path / "hello.txt").write_text("hi")
    r = executor.run_remote(["cat", "hello.txt"], remote_cwd="/mnt/local/output/dartrtest",
                            host="luism01", stage_in=[tmp_path / "hello.txt"], stage_out_dir=tmp_path)
    assert r.stdout.strip() == "hi"
