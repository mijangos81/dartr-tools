import os, pytest
from pathlib import Path
from dartr_tools import sandbox

@pytest.fixture
def wd(tmp_path):
    (tmp_path / "in.vcf").write_text("x")
    return tmp_path

def test_allows_workdir_input(wd):
    assert sandbox.resolve_input("in.vcf", wd) == (wd / "in.vcf").resolve()

def test_rejects_parent_escape(wd):
    with pytest.raises(sandbox.SandboxError):
        sandbox.resolve_input("../secret", wd)

def test_rejects_absolute_outside_allowlist(wd, monkeypatch):
    monkeypatch.delenv("DARTR_DATA_DIRS", raising=False)
    with pytest.raises(sandbox.SandboxError):
        sandbox.resolve_input("/etc/passwd", wd)

def test_allows_absolute_in_datadir(wd, tmp_path, monkeypatch):
    data = tmp_path / "data"; data.mkdir(); (data / "d.vcf").write_text("x")
    monkeypatch.setenv("DARTR_DATA_DIRS", str(data))
    assert sandbox.resolve_input(str(data / "d.vcf"), wd) == (data / "d.vcf").resolve()

def test_rejects_symlink_escape(wd, tmp_path):
    outside = tmp_path.parent / "outside.txt"; outside.write_text("secret")
    link = wd / "link.vcf"; os.symlink(outside, link)
    with pytest.raises(sandbox.SandboxError):
        sandbox.resolve_input("link.vcf", wd)

def test_output_must_be_in_workdir(wd):
    assert sandbox.resolve_output("out/res.rds", wd).is_relative_to(wd.resolve())
    with pytest.raises(sandbox.SandboxError):
        sandbox.resolve_output("/tmp/evil", wd)

def test_bounded():
    assert sandbox.bounded(5, 1, 20, "K") == 5
    with pytest.raises(sandbox.SandboxError):
        sandbox.bounded(0, 1, 20, "K")
