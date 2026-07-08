import pytest
from pathlib import Path
from dartr_tools import executor

def test_runs_and_captures(tmp_path):
    r = executor.run_local(["printf", "hello"], cwd=tmp_path)
    assert r.returncode == 0 and r.stdout == "hello"

def test_nonzero_raises(tmp_path):
    with pytest.raises(executor.ExecError) as e:
        executor.run_local(["sh", "-c", "exit 3"], cwd=tmp_path)
    assert e.value.result.returncode == 3

def test_dry_run_does_not_execute(tmp_path):
    marker = tmp_path / "m"
    r = executor.run_local(["touch", str(marker)], cwd=tmp_path, dry_run=True)
    assert not marker.exists() and "touch" in r.stdout

def test_env_scrubbed(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    r = executor.run_local(["sh", "-c", "echo ${OPENAI_API_KEY:-none}"], cwd=tmp_path)
    assert r.stdout.strip() == "none"

def test_timeout(tmp_path):
    with pytest.raises(executor.ExecError):
        executor.run_local(["sleep", "5"], cwd=tmp_path, timeout=1)
