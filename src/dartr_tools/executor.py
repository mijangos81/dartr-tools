import os, shlex, subprocess, time
from pathlib import Path
from typing import NamedTuple

_SECRET_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD")

class Result(NamedTuple):
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration: float

class ExecError(Exception):
    def __init__(self, result: Result):
        self.result = result
        super().__init__(f"command failed ({result.returncode}): {' '.join(result.argv)}\n{result.stderr[:500]}")

def _scrubbed_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not any(h in k.upper() for h in _SECRET_HINTS)}

def run_local(argv: list[str], cwd: Path, timeout: int | None = None, dry_run: bool = False) -> Result:
    if dry_run:
        return Result(argv, 0, " ".join(shlex.quote(a) for a in argv), "", 0.0)
    start = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=cwd, env=_scrubbed_env(), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise ExecError(Result(argv, 124, e.stdout or "", f"timeout after {timeout}s", time.monotonic() - start))
    res = Result(argv, p.returncode, p.stdout, p.stderr, time.monotonic() - start)
    if p.returncode != 0:
        raise ExecError(res)
    return res

def run_remote(argv, remote_cwd, host, stage_in, stage_out_dir, timeout=None, dry_run=False):
    remote_cmd = f"mkdir -p {shlex.quote(remote_cwd)} && cd {shlex.quote(remote_cwd)} && " + \
                 " ".join(shlex.quote(a) for a in argv)
    ssh = ["ssh", host, remote_cmd]
    if dry_run:
        return Result(ssh, 0, " ".join(shlex.quote(a) for a in ssh), "", 0.0)
    start = time.monotonic()
    for f in stage_in:
        subprocess.run(["rsync", "-az", str(f), f"{host}:{remote_cwd}/"], check=True, env=_scrubbed_env())
    p = subprocess.run(ssh, env=_scrubbed_env(), capture_output=True, text=True, timeout=timeout)
    subprocess.run(["rsync", "-az", f"{host}:{remote_cwd}/", str(stage_out_dir) + "/"], env=_scrubbed_env())
    res = Result(ssh, p.returncode, p.stdout, p.stderr, time.monotonic() - start)
    if p.returncode != 0:
        raise ExecError(res)
    return res
