import pytest
from dartr_tools import session

def test_creates_workdir(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    d = session.workdir("abc123")
    assert d.is_dir() and d.parent == tmp_path

def test_rejects_bad_id(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    with pytest.raises(ValueError):
        session.workdir("../escape")
