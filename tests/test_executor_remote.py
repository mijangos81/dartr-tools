import os, shlex, pytest
from dartr_tools import executor

def test_dry_run_builds_ssh(tmp_path):
    r = executor.run_remote(["admixture", "x.bed", "2"], remote_cwd="/mnt/local/output/s1",
                            host="luism01", stage_in=[], stage_out_dir=tmp_path, dry_run=True)
    assert "ssh" in r.stdout and "luism01" in r.stdout

def test_dry_run_quotes_shell_metacharacters(tmp_path):
    dangerous_cwd = "/mnt/local/output/s; rm -rf /"
    r = executor.run_remote(["echo", "x"], remote_cwd=dangerous_cwd,
                            host="luism01", stage_in=[], stage_out_dir=tmp_path, dry_run=True)
    # r.argv is ["ssh", host, remote_cmd] -- remote_cmd is the actual string that
    # gets interpreted by /bin/sh on the remote host, so it's the artifact that
    # matters for injection safety (r.stdout is only a re-quoted display string
    # and double-quotes, which makes naive substring checks on it unreliable).
    remote_cmd = r.argv[2]
    tokens = shlex.split(remote_cmd)
    # if the metacharacters were live, POSIX shell tokenizing would split
    # "; rm -rf /" into its own command instead of keeping it glued to the path
    assert tokens[:2] == ["mkdir", "-p"]
    assert tokens[2] == dangerous_cwd
    assert "rm" not in tokens

@pytest.mark.skipif(os.environ.get("DARTR_TEST_LUISM01") != "1", reason="luism01 not available")
def test_real_roundtrip(tmp_path):
    (tmp_path / "hello.txt").write_text("hi")
    r = executor.run_remote(["cat", "hello.txt"], remote_cwd="/mnt/local/output/dartrtest",
                            host="luism01", stage_in=[tmp_path / "hello.txt"], stage_out_dir=tmp_path)
    assert r.stdout.strip() == "hi"
