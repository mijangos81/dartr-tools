from pathlib import Path
from dartr_tools import config

def test_defaults(monkeypatch):
    for k in ("DARTR_PROGRAMS_DIR", "DARTR_DATA_DIRS", "DARTR_WORK_ROOT", "DARTR_LUISM01_HOST"):
        monkeypatch.delenv(k, raising=False)
    s = config.settings()
    assert s.programs_dir == Path.home() / "programs"
    assert s.work_root == Path.home() / ".dartr-tools" / "work"
    assert s.luism01_host == "luism01"
    assert s.local_timeout > 0

def test_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(tmp_path / "p"))
    monkeypatch.setenv("DARTR_DATA_DIRS", f"{tmp_path/'a'}:{tmp_path/'b'}")
    s = config.settings()
    assert s.programs_dir == tmp_path / "p"
    assert (tmp_path / "a") in s.data_dirs and (tmp_path / "b") in s.data_dirs
