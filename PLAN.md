# dartr-tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python MCP server that exposes a curated, guardrailed set of population-genetics tools (local `~/programs` binaries + dartRverse functions) as typed, agent-callable tools for Claude Code and opencode.

**Architecture:** A `FastMCP` server registers nine typed tools. Each tool validates its inputs through a path sandbox, then dispatches to one of three backends via a shared executor: a local binary (resolved from a pinned registry), a dartRverse call (a fixed-dispatch `Rscript` runner — no R `eval`), or a remote run on the luism01 VM (ssh/rsync under `dart-compute` rules). Every call appends a provenance record. Data moves between tools as file paths in a per-session workdir, never through the model.

**Tech Stack:** Python 3.11+, `uv` (project + runner), `mcp` (FastMCP server), Pydantic v2 (typed tool args), `pytest` (real-implementation tests, no mocks), `Rscript` bridge to dartRverse, `ssh`/`rsync` to luism01.

## Global Constraints

- **No generic shell tool.** Only the nine defined tools are exposed. Never add a passthrough command tool.
- **Injection-proof.** Arguments pass to subprocesses as `argv` lists and to R as a JSON data file. Never build a shell string; never `Rscript -e` with interpolated user input. The R runner dispatches on a fixed `switch(fn, ...)` over an allowlist.
- **Path sandbox.** Every input/output path must resolve (after `realpath`) inside an allowed root: the session workdir or a configured data-dir allowlist. Reject `..` escapes, absolute paths outside the allowlist, and symlinks pointing outside. Bound numeric params (e.g. `K ∈ 1..20`, `callrate ∈ 0..1`).
- **Inputs read-only.** Copy inputs into the session workdir; never mutate a source file. Outputs go only under the session workdir (or `/mnt/local/output` remotely).
- **Binaries resolved from `~/programs`.** Never from `PATH`, never copied into the repo. Pinned in `registry.py`.
- **dartRverse, not dartR.** The R runner uses `library(dartRverse)`. Function names are pinned against the live NAMESPACE (see Task 8 allowlist).
- **Credentials scrubbed** from every subprocess environment.
- **Provenance.** Every tool call appends one JSONL record to the session manifest.
- **Tests use real implementations** against a tiny fixture VCF. R- and luism01-dependent tests `skip` (not fail) when the dependency is unavailable.

---

## File Structure

```
dartr-tools/
  pyproject.toml                  # uv project; deps: mcp, pydantic; dev: pytest
  src/dartr_tools/
    __init__.py
    server.py                     # FastMCP instance, tool registration, entry point
    config.py                     # Settings: programs dir, data-dir allowlist, luism01 host, timeouts, work root
    session.py                    # Per-session workdir resolution
    sandbox.py                    # Path validation + numeric bounds (security-critical)
    registry.py                   # Pinned binary registry (name -> ~/programs path)
    executor.py                   # run_local / run_remote: argv, cwd, timeout, env scrub
    provenance.py                 # Append run manifest (JSONL), input hashing
    rbridge.py                    # dartRverse call: write args JSON, run runner.R, parse paths
    r/runner.R                    # Fixed-dispatch Rscript runner over the gl.* allowlist
    tools/
      __init__.py                 # register_all(mcp)
      io.py                       # read_vcf, convert
      filter.py                   # filter_snps
      report.py                   # report_diversity, report_fst, pcoa
      admixture.py                # run_admixture
      relatedness.py              # run_relatedness
      ne.py                       # estimate_ne
  tests/
    conftest.py                   # fixtures: tiny VCF, session workdir, dependency skips
    fixtures/tiny.vcf             # ~200 SNPs, 3 populations
    test_sandbox.py
    test_registry.py
    test_executor.py
    test_provenance.py
    test_rbridge.py               # skipped if R/dartRverse unavailable
    test_tools_io.py
    test_tools_filter.py
    test_tools_report.py
    test_tools_admixture.py
    test_tools_relatedness.py
    test_tools_ne.py
```

Each `tools/*.py` module owns a small group of tools that share a backend and helper shape. Infrastructure (`sandbox`, `registry`, `executor`, `provenance`, `rbridge`) is split by responsibility so each file stays focused and independently testable.

---

## Task 1: Project scaffold + walking-skeleton server

Prove the MCP server boots and exposes a tool end-to-end before any science.

**Files:**
- Create: `pyproject.toml`, `src/dartr_tools/__init__.py`, `src/dartr_tools/server.py`
- Test: `tests/test_server.py`, `tests/conftest.py`

**Interfaces:**
- Produces: `server.mcp` (a `FastMCP` instance); `server.main()` entry point; a `status()` tool returning `{"name": "dartr-tools", "version": <str>, "tools": <int>}`.

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "dartr-tools"
version = "0.1.0"
description = "MCP server exposing the local popgen toolkit (~/programs + dartRverse) to AI agents"
requires-python = ">=3.11"
dependencies = ["mcp>=1.2", "pydantic>=2"]

[project.scripts]
dartr-tools = "dartr_tools.server:main"

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_server.py
from dartr_tools import server

def test_status_tool_registered():
    names = {t.name for t in server.mcp._tool_manager.list_tools()}
    assert "status" in names

def test_status_returns_metadata():
    out = server.status()
    assert out["name"] == "dartr-tools"
    assert isinstance(out["version"], str) and out["version"]
    assert out["tools"] >= 1
```

- [ ] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/test_server.py -v`
Expected: FAIL (`ModuleNotFoundError: dartr_tools.server`)

- [ ] **Step 4: Write minimal implementation**

```python
# src/dartr_tools/__init__.py
__version__ = "0.1.0"
```

```python
# src/dartr_tools/server.py
from importlib.metadata import version, PackageNotFoundError
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("dartr-tools")

def _version() -> str:
    try:
        return version("dartr-tools")
    except PackageNotFoundError:
        return "0.0.0-dev"

@mcp.tool()
def status() -> dict:
    """Report server name, version, and number of registered tools."""
    return {"name": "dartr-tools", "version": _version(), "tools": len(mcp._tool_manager.list_tools())}

def main() -> None:
    mcp.run()

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_server.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/dartr_tools/__init__.py src/dartr_tools/server.py tests/test_server.py
git commit -m "feat: MCP walking skeleton with status tool"
```

---

## Task 2: Config

**Files:**
- Create: `src/dartr_tools/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `config.settings()` → a frozen `Settings` with `programs_dir: Path`, `data_dirs: list[Path]`, `work_root: Path`, `luism01_host: str`, `local_timeout: int`, `remote_timeout: int`. All overridable by env vars (`DARTR_PROGRAMS_DIR`, `DARTR_DATA_DIRS` (colon-separated), `DARTR_WORK_ROOT`, `DARTR_LUISM01_HOST`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# src/dartr_tools/config.py
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    programs_dir: Path
    data_dirs: list[Path]
    work_root: Path
    luism01_host: str
    local_timeout: int
    remote_timeout: int

def _paths(env: str) -> list[Path]:
    raw = os.environ.get(env, "")
    return [Path(p).expanduser() for p in raw.split(":") if p]

def settings() -> Settings:
    return Settings(
        programs_dir=Path(os.environ.get("DARTR_PROGRAMS_DIR", str(Path.home() / "programs"))).expanduser(),
        data_dirs=_paths("DARTR_DATA_DIRS"),
        work_root=Path(os.environ.get("DARTR_WORK_ROOT", str(Path.home() / ".dartr-tools" / "work"))).expanduser(),
        luism01_host=os.environ.get("DARTR_LUISM01_HOST", "luism01"),
        local_timeout=int(os.environ.get("DARTR_LOCAL_TIMEOUT", "1800")),
        remote_timeout=int(os.environ.get("DARTR_REMOTE_TIMEOUT", "21600")),
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/config.py tests/test_config.py
git commit -m "feat: config settings with env overrides"
```

---

## Task 3: Session workdir

**Files:**
- Create: `src/dartr_tools/session.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Produces: `session.workdir(session_id: str) -> Path` — creates and returns `work_root/<safe-id>/`. `session_id` is sanitised to `[A-Za-z0-9_-]` (reject anything else).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_session.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_session.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/dartr_tools/session.py
import re
from pathlib import Path
from .config import settings

_SAFE = re.compile(r"^[A-Za-z0-9_-]+$")

def workdir(session_id: str) -> Path:
    if not _SAFE.match(session_id):
        raise ValueError(f"unsafe session id: {session_id!r}")
    d = settings().work_root / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_session.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/session.py tests/test_session.py
git commit -m "feat: per-session workdir with id sanitisation"
```

---

## Task 4: Path sandbox (security-critical)

**Files:**
- Create: `src/dartr_tools/sandbox.py`
- Test: `tests/test_sandbox.py`

**Interfaces:**
- Produces:
  - `sandbox.resolve_input(path: str, workdir: Path) -> Path` — resolves and asserts the path is inside `workdir` or a configured data dir; raises `SandboxError` otherwise.
  - `sandbox.resolve_output(path: str, workdir: Path) -> Path` — asserts the path is inside `workdir`; raises `SandboxError` otherwise.
  - `sandbox.bounded(value, lo, hi, name) -> <number>` — raises `SandboxError` if out of `[lo, hi]`.
  - `class SandboxError(Exception)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sandbox.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_sandbox.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/dartr_tools/sandbox.py
from pathlib import Path
from .config import settings

class SandboxError(Exception):
    pass

def _roots(workdir: Path) -> list[Path]:
    return [workdir.resolve(), *(d.resolve() for d in settings().data_dirs)]

def _within(p: Path, roots: list[Path]) -> bool:
    return any(p == r or p.is_relative_to(r) for r in roots)

def resolve_input(path: str, workdir: Path) -> Path:
    p = (workdir / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not _within(p, _roots(workdir)):
        raise SandboxError(f"input path outside allowed roots: {path}")
    return p

def resolve_output(path: str, workdir: Path) -> Path:
    root = workdir.resolve()
    p = (workdir / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not (p == root or p.is_relative_to(root)):
        raise SandboxError(f"output path must be inside the session workdir: {path}")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def bounded(value, lo, hi, name):
    if value < lo or value > hi:
        raise SandboxError(f"{name}={value} out of range [{lo}, {hi}]")
    return value
```

Note: `Path.resolve()` collapses symlinks, so a symlink pointing outside the roots resolves to its outside target and is correctly rejected by `_within`.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_sandbox.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/sandbox.py tests/test_sandbox.py
git commit -m "feat: path sandbox with escape/symlink/bounds guards"
```

---

## Task 5: Binary registry

**Files:**
- Create: `src/dartr_tools/registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Produces: `registry.resolve(name: str) -> Path` — maps a logical name to `programs_dir/<file>` from a pinned `BINARIES` dict; raises `RegistryError` if the name is unknown or the file is missing/not executable. `registry.BINARIES: dict[str, str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_registry.py
import os, stat, pytest
from dartr_tools import registry

def test_known_names_present():
    assert {"admixture", "emibd9", "ne2"} <= set(registry.BINARIES)

def test_resolve_ok(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(tmp_path))
    b = tmp_path / registry.BINARIES["admixture"]
    b.write_text("#!/bin/sh\n"); b.chmod(b.stat().st_mode | stat.S_IEXEC)
    assert registry.resolve("admixture") == b.resolve()

def test_resolve_unknown(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(tmp_path))
    with pytest.raises(registry.RegistryError):
        registry.resolve("rm")

def test_resolve_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(tmp_path))
    with pytest.raises(registry.RegistryError):
        registry.resolve("admixture")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_registry.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/dartr_tools/registry.py
import os
from pathlib import Path
from .config import settings

class RegistryError(Exception):
    pass

# Logical name -> filename under ~/programs (pinned; never PATH-resolved).
BINARIES: dict[str, str] = {
    "admixture": "admixture",
    "emibd9": "EM_IBD_P",
    "ne2": "Ne2-1M",
    "plink": "plink",
}

def resolve(name: str) -> Path:
    if name not in BINARIES:
        raise RegistryError(f"unknown binary: {name}")
    p = (settings().programs_dir / BINARIES[name]).resolve()
    if not p.is_file() or not os.access(p, os.X_OK):
        raise RegistryError(f"binary not found or not executable: {p}")
    return p
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/registry.py tests/test_registry.py
git commit -m "feat: pinned ~/programs binary registry"
```

---

## Task 6: Executor (local)

**Files:**
- Create: `src/dartr_tools/executor.py`
- Test: `tests/test_executor.py`

**Interfaces:**
- Produces:
  - `class Result(NamedTuple): argv: list[str]; returncode: int; stdout: str; stderr: str; duration: float`
  - `executor.run_local(argv: list[str], cwd: Path, timeout: int | None = None, dry_run: bool = False) -> Result`
  - `class ExecError(Exception)` with `.result: Result`.
  - Env is scrubbed: keys matching `*KEY*`, `*TOKEN*`, `*SECRET*`, `*PASSWORD*` (case-insensitive) removed.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_executor.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_executor.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/dartr_tools/executor.py
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_executor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/executor.py tests/test_executor.py
git commit -m "feat: local executor with timeout, env scrub, dry-run"
```

---

## Task 7: Provenance

**Files:**
- Create: `src/dartr_tools/provenance.py`
- Test: `tests/test_provenance.py`

**Interfaces:**
- Produces: `provenance.record(workdir: Path, tool: str, args: dict, inputs: list[Path], outputs: list[Path], exit_code: int) -> dict` — appends one JSON line to `workdir/provenance.jsonl` and returns the record. Inputs are hashed (sha256, first 16 hex). Timestamp is passed in via `args["_ts"]` if present else `"unstamped"` (scripts have no clock; the server injects it).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_provenance.py
import json
from pathlib import Path
from dartr_tools import provenance

def test_appends_record(tmp_path):
    f = tmp_path / "in.txt"; f.write_text("abc")
    rec = provenance.record(tmp_path, "read_vcf", {"x": 1}, [f], [tmp_path / "out.rds"], 0)
    lines = (tmp_path / "provenance.jsonl").read_text().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["tool"] == "read_vcf" and parsed["exit_code"] == 0
    assert parsed["inputs"][0]["sha256"] and parsed["outputs"] == ["out.rds"]

def test_two_calls_append(tmp_path):
    provenance.record(tmp_path, "a", {}, [], [], 0)
    provenance.record(tmp_path, "b", {}, [], [], 0)
    assert len((tmp_path / "provenance.jsonl").read_text().splitlines()) == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_provenance.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/dartr_tools/provenance.py
import hashlib, json
from pathlib import Path

def _hash(p: Path) -> str:
    if not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def record(workdir: Path, tool: str, args: dict, inputs: list[Path], outputs: list[Path], exit_code: int) -> dict:
    rec = {
        "ts": args.get("_ts", "unstamped"),
        "tool": tool,
        "args": {k: v for k, v in args.items() if not k.startswith("_")},
        "inputs": [{"path": str(p), "sha256": _hash(p)} for p in inputs],
        "outputs": [str(p.relative_to(workdir)) if p.is_relative_to(workdir) else str(p) for p in outputs],
        "exit_code": exit_code,
    }
    with (workdir / "provenance.jsonl").open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_provenance.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/provenance.py tests/test_provenance.py
git commit -m "feat: provenance manifest with input hashing"
```

---

## Task 8: dartRverse bridge + R runner

**Files:**
- Create: `src/dartr_tools/rbridge.py`, `src/dartr_tools/r/runner.R`
- Test: `tests/test_rbridge.py`, `tests/conftest.py` (add `have_r` skip helper)

**Interfaces:**
- Produces: `rbridge.call_gl(fn: str, params: dict, workdir: Path, timeout: int | None = None, dry_run: bool = False) -> dict` — writes `params` (already containing resolved absolute paths under `workdir`) to `workdir/_rreq.json`, runs `Rscript runner.R <req.json>`, and returns the JSON the runner prints (must include `{"outputs": [<relpaths>]}`). Raises `executor.ExecError` on non-zero. `rbridge.ALLOW: set[str]` mirrors the runner allowlist.
- The runner performs a **fixed `switch(fn, ...)`** — no `eval`, no `get(fn)()`. Each branch is hand-written R.

- [ ] **Step 1: Write the allowlisted runner**

```r
# src/dartr_tools/r/runner.R  — fixed-dispatch dartRverse runner (no eval)
suppressWarnings(suppressMessages({
  library(jsonlite); library(dartRverse)
}))
args <- commandArgs(trailingOnly = TRUE)
req  <- jsonlite::fromJSON(args[[1]], simplifyVector = TRUE)
fn   <- req$fn
p    <- req$params
outdir <- req$workdir

emit <- function(outputs) cat(jsonlite::toJSON(list(outputs = outputs), auto_unbox = TRUE))

if (fn == "gl.read.vcf") {
  gl  <- gl.read.vcf(p$vcf, verbose = 0)
  out <- file.path(outdir, p$out); saveRDS(gl, out); emit(c(p$out))

} else if (fn == "gl.filter") {                       # generic filter chain, fixed ops only
  gl <- readRDS(p$rds)
  if (!is.null(p$callrate)) gl <- gl.filter.callrate(gl, threshold = p$callrate, verbose = 0)
  if (!is.null(p$maf))      gl <- gl.filter.maf(gl, threshold = p$maf, verbose = 0)
  if (!is.null(p$rdepth))   gl <- gl.filter.rdepth(gl, lower = p$rdepth, verbose = 0)
  if (isTRUE(p$monomorphs)) gl <- gl.filter.monomorphs(gl, verbose = 0)
  out <- file.path(outdir, p$out); saveRDS(gl, out); emit(c(p$out))

} else if (fn == "gl2plink") {
  gl <- readRDS(p$rds); gl2plink(gl, outfile = p$out, outpath = outdir, verbose = 0)
  emit(c(paste0(p$out, ".ped"), paste0(p$out, ".map")))

} else if (fn == "gl2vcf") {
  gl <- readRDS(p$rds); gl2vcf(gl, outfile = p$out, outpath = outdir, verbose = 0)
  emit(c(paste0(p$out, ".vcf")))

} else if (fn == "gl.report.heterozygosity") {
  gl <- readRDS(p$rds); res <- gl.report.heterozygosity(gl, verbose = 0)
  out <- file.path(outdir, p$out); write.csv(res, out, row.names = FALSE); emit(c(p$out))

} else if (fn == "gl.fst.pop") {
  gl <- readRDS(p$rds); res <- gl.fst.pop(gl, verbose = 0)
  out <- file.path(outdir, p$out); saveRDS(res, out); emit(c(p$out))

} else if (fn == "gl.pcoa") {
  gl <- readRDS(p$rds); pc <- gl.pcoa(gl, verbose = 0)
  co <- file.path(outdir, p$out_coords); saveRDS(pc, co)
  pl <- file.path(outdir, p$out_plot)
  ggplot2::ggsave(pl, gl.pcoa.plot(pc, gl, verbose = 0), width = 7, height = 6)
  emit(c(p$out_coords, p$out_plot))

} else if (fn == "gl.LDNe") {
  gl <- readRDS(p$rds)
  res <- gl.LDNe(gl, outfile = p$out, outpath = outdir, neest.path = p$neest_path, verbose = 0)
  out <- file.path(outdir, "ne.rds"); saveRDS(res, out); emit(c("ne.rds"))

} else {
  stop(paste("function not allowed:", fn))
}
```

- [ ] **Step 2: Write `rbridge.py` + failing test**

```python
# src/dartr_tools/rbridge.py
import json
from pathlib import Path
from . import executor

ALLOW = {"gl.read.vcf", "gl.filter", "gl2plink", "gl2vcf",
         "gl.report.heterozygosity", "gl.fst.pop", "gl.pcoa", "gl.LDNe"}
_RUNNER = Path(__file__).parent / "r" / "runner.R"

def call_gl(fn: str, params: dict, workdir: Path, timeout: int | None = None, dry_run: bool = False) -> dict:
    if fn not in ALLOW:
        raise ValueError(f"gl function not allowed: {fn}")
    req = {"fn": fn, "params": params, "workdir": str(workdir)}
    reqfile = workdir / "_rreq.json"
    reqfile.write_text(json.dumps(req))
    res = executor.run_local(["Rscript", str(_RUNNER), str(reqfile)], cwd=workdir, timeout=timeout, dry_run=dry_run)
    if dry_run:
        return {"outputs": [], "dry_run": res.stdout}
    return json.loads(res.stdout)
```

```python
# tests/test_rbridge.py
import shutil, pytest
from pathlib import Path
from dartr_tools import rbridge

pytestmark = pytest.mark.skipif(
    shutil.which("Rscript") is None, reason="Rscript not available")

def test_rejects_unlisted_fn(tmp_path):
    with pytest.raises(ValueError):
        rbridge.call_gl("system", {}, tmp_path)

def test_read_vcf_roundtrip(tmp_path, tiny_vcf):
    shutil.copy(tiny_vcf, tmp_path / "in.vcf")
    out = rbridge.call_gl("gl.read.vcf", {"vcf": str(tmp_path / "in.vcf"), "out": "gl.rds"}, tmp_path)
    assert (tmp_path / "gl.rds").is_file() and out["outputs"] == ["gl.rds"]
```

Add to `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def tiny_vcf() -> Path:
    return Path(__file__).parent / "fixtures" / "tiny.vcf"
```

- [ ] **Step 3: Create the fixture VCF**

Write `tests/fixtures/tiny.vcf` — a minimal valid VCF with ~20 SNPs across 6 samples labelled into 3 populations via a companion `tiny.pop` (or use sample-name prefixes `popA_1`…). Keep it tiny but real enough for `gl.read.vcf`. (Hand-author or generate once with `bcftools`; commit the static file so tests are deterministic.)

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_rbridge.py -v`
Expected: PASS where `Rscript` + dartRverse present; SKIPPED otherwise.

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/rbridge.py src/dartr_tools/r/runner.R tests/test_rbridge.py tests/conftest.py tests/fixtures/tiny.vcf
git commit -m "feat: dartRverse bridge with fixed-dispatch R runner"
```

---

## Task 9: `read_vcf` + `convert` tools (I/O)

Establishes the dartRverse tool pattern: Pydantic-validated args → sandbox → `call_gl` → provenance → return output paths.

**Files:**
- Create: `src/dartr_tools/tools/__init__.py`, `src/dartr_tools/tools/io.py`
- Modify: `src/dartr_tools/server.py` (call `tools.register_all(mcp)`)
- Test: `tests/test_tools_io.py`

**Interfaces:**
- Consumes: `sandbox.resolve_input/resolve_output`, `session.workdir`, `rbridge.call_gl`, `provenance.record`.
- Produces: MCP tools `read_vcf(session_id, vcf, out="gl.rds")` and `convert(session_id, rds, fmt, out)`; `tools.register_all(mcp)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tools_io.py
import shutil, pytest
from pathlib import Path
from dartr_tools.tools import io

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")

def test_read_vcf(monkeypatch, tmp_path, tiny_vcf):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    out = io.read_vcf("s1", str(tiny_vcf), out="gl.rds")
    assert out["outputs"] == ["gl.rds"]
    wd = tmp_path / "s1"
    assert (wd / "gl.rds").is_file()
    assert (wd / "provenance.jsonl").is_file()
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_tools_io.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# src/dartr_tools/tools/io.py
from ..session import workdir
from ..sandbox import resolve_input, resolve_output
from ..rbridge import call_gl
from ..provenance import record

def read_vcf(session_id: str, vcf: str, out: str = "gl.rds") -> dict:
    """Load a VCF into a dartRverse genlight object (saved as .RDS)."""
    wd = workdir(session_id)
    vin = resolve_input(vcf, wd)
    resolve_output(out, wd)
    res = call_gl("gl.read.vcf", {"vcf": str(vin), "out": out}, wd)
    record(wd, "read_vcf", {"vcf": str(vin), "out": out}, [vin], [wd / out], 0)
    return res

def convert(session_id: str, rds: str, fmt: str, out: str) -> dict:
    """Convert a genlight RDS to PLINK ('plink') or VCF ('vcf')."""
    wd = workdir(session_id)
    rin = resolve_input(rds, wd)
    resolve_output(out, wd)
    fn = {"plink": "gl2plink", "vcf": "gl2vcf"}.get(fmt)
    if fn is None:
        raise ValueError("fmt must be 'plink' or 'vcf'")
    res = call_gl(fn, {"rds": str(rin), "out": out}, wd)
    record(wd, "convert", {"rds": str(rin), "fmt": fmt, "out": out}, [rin], [wd / o for o in res["outputs"]], 0)
    return res
```

```python
# src/dartr_tools/tools/__init__.py
from . import io

def register_all(mcp) -> None:
    mcp.tool()(io.read_vcf)
    mcp.tool()(io.convert)
```

Modify `server.py` — after defining `mcp` and `status`, add:

```python
from . import tools
tools.register_all(mcp)
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_tools_io.py tests/test_server.py -v`
Expected: PASS / SKIP (io tests skip without Rscript; server tests pass and now count more tools)

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/tools/ src/dartr_tools/server.py tests/test_tools_io.py
git commit -m "feat: read_vcf + convert tools (dartRverse pattern)"
```

---

## Task 10: `filter_snps` tool

**Files:**
- Create: `src/dartr_tools/tools/filter.py`; **Modify:** `tools/__init__.py`
- Test: `tests/test_tools_filter.py`

**Interfaces:**
- Produces: `filter_snps(session_id, rds, callrate=None, maf=None, rdepth=None, monomorphs=False, out="filtered.rds")`.

- [ ] **Step 1: Failing test**

```python
# tests/test_tools_filter.py
import shutil, pytest
from dartr_tools.tools import io, filter as flt

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")

def test_filter(monkeypatch, tmp_path, tiny_vcf):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    io.read_vcf("s", str(tiny_vcf))
    out = flt.filter_snps("s", "gl.rds", callrate=0.5, maf=0.05, out="f.rds")
    assert out["outputs"] == ["f.rds"] and (tmp_path / "s" / "f.rds").is_file()
```

- [ ] **Step 2: Run — expect FAIL.** `uv run pytest tests/test_tools_filter.py -v`

- [ ] **Step 3: Implement**

```python
# src/dartr_tools/tools/filter.py
from ..session import workdir
from ..sandbox import resolve_input, resolve_output, bounded
from ..rbridge import call_gl
from ..provenance import record

def filter_snps(session_id: str, rds: str, callrate: float | None = None, maf: float | None = None,
                rdepth: int | None = None, monomorphs: bool = False, out: str = "filtered.rds") -> dict:
    """Filter SNPs by call rate / MAF / read depth, optionally dropping monomorphs."""
    wd = workdir(session_id)
    rin = resolve_input(rds, wd); resolve_output(out, wd)
    if callrate is not None: bounded(callrate, 0, 1, "callrate")
    if maf is not None: bounded(maf, 0, 0.5, "maf")
    params = {"rds": str(rin), "callrate": callrate, "maf": maf, "rdepth": rdepth,
              "monomorphs": monomorphs, "out": out}
    res = call_gl("gl.filter", params, wd)
    record(wd, "filter_snps", params, [rin], [wd / out], 0)
    return res
```

Add to `tools/__init__.py`: `from . import filter as _filter` and in `register_all`: `mcp.tool()(_filter.filter_snps)`.

- [ ] **Step 4: Run — expect PASS/SKIP.** `uv run pytest tests/test_tools_filter.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/tools/filter.py src/dartr_tools/tools/__init__.py tests/test_tools_filter.py
git commit -m "feat: filter_snps tool"
```

---

## Task 11: `report_diversity`, `report_fst`, `pcoa` tools

Three read-only dartRverse analyses in one module (they share shape; each has its own test + commit).

**Files:**
- Create: `src/dartr_tools/tools/report.py`; **Modify:** `tools/__init__.py`
- Test: `tests/test_tools_report.py`

**Interfaces:**
- Produces: `report_diversity(session_id, rds, out="diversity.csv")`; `report_fst(session_id, rds, out="fst.rds")`; `pcoa(session_id, rds, out_coords="pcoa.rds", out_plot="pcoa.png")`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_tools_report.py
import shutil, pytest
from dartr_tools.tools import io, report

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")

def _prep(monkeypatch, tmp_path, tiny_vcf):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    io.read_vcf("s", str(tiny_vcf))

def test_diversity(monkeypatch, tmp_path, tiny_vcf):
    _prep(monkeypatch, tmp_path, tiny_vcf)
    assert report.report_diversity("s", "gl.rds")["outputs"] == ["diversity.csv"]

def test_fst(monkeypatch, tmp_path, tiny_vcf):
    _prep(monkeypatch, tmp_path, tiny_vcf)
    assert report.report_fst("s", "gl.rds")["outputs"] == ["fst.rds"]

def test_pcoa(monkeypatch, tmp_path, tiny_vcf):
    _prep(monkeypatch, tmp_path, tiny_vcf)
    out = report.pcoa("s", "gl.rds")
    assert set(out["outputs"]) == {"pcoa.rds", "pcoa.png"}
```

- [ ] **Step 2: Run — expect FAIL.** `uv run pytest tests/test_tools_report.py -v`

- [ ] **Step 3: Implement**

```python
# src/dartr_tools/tools/report.py
from ..session import workdir
from ..sandbox import resolve_input, resolve_output
from ..rbridge import call_gl
from ..provenance import record

def report_diversity(session_id: str, rds: str, out: str = "diversity.csv") -> dict:
    """Per-population heterozygosity / diversity report (CSV)."""
    wd = workdir(session_id); rin = resolve_input(rds, wd); resolve_output(out, wd)
    res = call_gl("gl.report.heterozygosity", {"rds": str(rin), "out": out}, wd)
    record(wd, "report_diversity", {"rds": str(rin), "out": out}, [rin], [wd / out], 0)
    return res

def report_fst(session_id: str, rds: str, out: str = "fst.rds") -> dict:
    """Pairwise Fst between populations (saved as .RDS)."""
    wd = workdir(session_id); rin = resolve_input(rds, wd); resolve_output(out, wd)
    res = call_gl("gl.fst.pop", {"rds": str(rin), "out": out}, wd)
    record(wd, "report_fst", {"rds": str(rin), "out": out}, [rin], [wd / out], 0)
    return res

def pcoa(session_id: str, rds: str, out_coords: str = "pcoa.rds", out_plot: str = "pcoa.png") -> dict:
    """Principal-coordinates ordination with a plot."""
    wd = workdir(session_id); rin = resolve_input(rds, wd)
    resolve_output(out_coords, wd); resolve_output(out_plot, wd)
    params = {"rds": str(rin), "out_coords": out_coords, "out_plot": out_plot}
    res = call_gl("gl.pcoa", params, wd)
    record(wd, "pcoa", params, [rin], [wd / out_coords, wd / out_plot], 0)
    return res
```

Register all three in `tools/__init__.py`.

- [ ] **Step 4: Run — expect PASS/SKIP.** `uv run pytest tests/test_tools_report.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/tools/report.py src/dartr_tools/tools/__init__.py tests/test_tools_report.py
git commit -m "feat: report_diversity, report_fst, pcoa tools"
```

---

## Task 12: Remote executor (luism01 routing)

**Files:**
- Modify: `src/dartr_tools/executor.py` (add `run_remote`)
- Test: `tests/test_executor_remote.py`

**Interfaces:**
- Produces: `executor.run_remote(argv, remote_cwd, host, stage_in: list[Path], stage_out_dir: Path, timeout, dry_run) -> Result` — `rsync` `stage_in` files to `<host>:<remote_cwd>/`, `ssh <host>` runs the command with `remote_cwd` as working dir under `dart-compute` rules (output to `/mnt/local/output`), then `rsync` results back into `stage_out_dir`. Uses the configured `ssh`/`rsync` (respecting the `luism01` alias); no interactive auth. Reuses `_scrubbed_env`.

- [ ] **Step 1: Failing test** (real ssh is gated behind an env flag so CI/laptop skips)

```python
# tests/test_executor_remote.py
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
```

- [ ] **Step 2: Run — expect FAIL** (dry-run test) `uv run pytest tests/test_executor_remote.py -v`

- [ ] **Step 3: Implement `run_remote`**

```python
# append to src/dartr_tools/executor.py
import shlex, subprocess, time

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
```

- [ ] **Step 4: Run — expect PASS (dry-run) / SKIP (real).** `uv run pytest tests/test_executor_remote.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/executor.py tests/test_executor_remote.py
git commit -m "feat: remote executor (rsync+ssh) for luism01 under dart-compute rules"
```

---

## Task 13: `run_admixture` tool (binary + routing)

Establishes the binary-tool pattern and local/remote escalation.

**Files:**
- Create: `src/dartr_tools/tools/admixture.py`; **Modify:** `tools/__init__.py`
- Test: `tests/test_tools_admixture.py`

**Interfaces:**
- Consumes: `registry.resolve("admixture")`, `convert(...)` (to produce PLINK input), `executor.run_local/run_remote`, `sandbox.bounded`.
- Produces: `run_admixture(session_id, rds, k_min=2, k_max=6, heavy=False, snp_threshold=200000)` → runs `admixture --cv` per K, parses CV error, returns `{"outputs": [...Q/P files...], "cv": {K: error}}`. Auto-escalates to luism01 when `heavy` or the PLINK `.bim` SNP count exceeds `snp_threshold`.

- [ ] **Step 1: Failing test** (uses a stub `admixture` on `DARTR_PROGRAMS_DIR` so it runs without the real binary or R)

```python
# tests/test_tools_admixture.py
import os, stat, textwrap, pytest
from pathlib import Path
from dartr_tools.tools import admixture

def _stub(progdir: Path):
    b = progdir / "admixture"
    b.write_text(textwrap.dedent("""\
        #!/bin/sh
        # emit fake CV line + Q/P files named like admixture does
        K=$3
        echo "CV error (K=$K): 0.4$K"
        base=$(basename "$2" .bed)
        : > "${base}.${K}.Q"; : > "${base}.${K}.P"
    """))
    b.chmod(b.stat().st_mode | stat.S_IEXEC)

def test_admixture_local(monkeypatch, tmp_path):
    prog = tmp_path / "prog"; prog.mkdir(); _stub(prog)
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(prog))
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path / "work"))
    wd = tmp_path / "work" / "s"; wd.mkdir(parents=True)
    for ext in ("bed", "bim", "fam"):
        (wd / f"in.{ext}").write_text("snp1\nsnp2\n")   # 2-line .bim => 2 SNPs
    out = admixture.run_admixture("s", plink="in", k_min=2, k_max=3)
    assert set(out["cv"]) == {2, 3} and out["cv"][2] == 0.42
```

- [ ] **Step 2: Run — expect FAIL.** `uv run pytest tests/test_tools_admixture.py -v`

- [ ] **Step 3: Implement**

```python
# src/dartr_tools/tools/admixture.py
import re
from pathlib import Path
from ..session import workdir
from ..sandbox import resolve_input, bounded
from ..registry import resolve
from ..config import settings
from ..executor import run_local, run_remote
from ..provenance import record

_CV = re.compile(r"CV error \(K=(\d+)\):\s*([0-9.]+)")

def run_admixture(session_id: str, plink: str, k_min: int = 2, k_max: int = 6,
                  heavy: bool = False, snp_threshold: int = 200_000) -> dict:
    """Run ADMIXTURE with cross-validation across a K range on a PLINK bfile prefix."""
    wd = workdir(session_id)
    bounded(k_min, 1, 20, "k_min"); bounded(k_max, k_min, 20, "k_max")
    bed = resolve_input(f"{plink}.bed", wd)
    nsnp = sum(1 for _ in (wd / f"{plink}.bim").open())
    binary = resolve("admixture")
    remote = heavy or nsnp > snp_threshold
    cv, outputs = {}, []
    for k in range(k_min, k_max + 1):
        argv = [str(binary), "--cv", str(bed), str(k)]
        if remote:
            r = run_remote(argv, remote_cwd=f"/mnt/local/output/{session_id}", host=settings().luism01_host,
                           stage_in=[wd / f"{plink}.{e}" for e in ("bed", "bim", "fam")],
                           stage_out_dir=wd, timeout=settings().remote_timeout)
        else:
            r = run_local(argv, cwd=wd, timeout=settings().local_timeout)
        m = _CV.search(r.stdout)
        if m:
            cv[int(m.group(1))] = float(m.group(2))
        outputs += [f"{plink}.{k}.Q", f"{plink}.{k}.P"]
    record(wd, "run_admixture", {"plink": plink, "k_min": k_min, "k_max": k_max, "remote": remote},
           [bed], [wd / o for o in outputs], 0)
    return {"outputs": outputs, "cv": cv}
```

Register in `tools/__init__.py`.

- [ ] **Step 4: Run — expect PASS.** `uv run pytest tests/test_tools_admixture.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/tools/admixture.py src/dartr_tools/tools/__init__.py tests/test_tools_admixture.py
git commit -m "feat: run_admixture tool with CV parse + luism01 routing"
```

---

## Task 14: `run_relatedness` tool

**Files:**
- Create: `src/dartr_tools/tools/relatedness.py`; **Modify:** `tools/__init__.py`
- Test: `tests/test_tools_relatedness.py`

**Interfaces:**
- Consumes: `registry.resolve("emibd9")`, `executor.run_local/run_remote`.
- Produces: `run_relatedness(session_id, plink, heavy=False)` → runs EMIBD9 on the PLINK prefix, returns `{"outputs": [<relatedness matrix file>]}`. **Open question §8.1:** if a `gl.run.emibd9` dartRverse wrapper is confirmed on a dev branch during implementation, prefer routing through `rbridge` instead of the raw binary; adjust this task accordingly and note it in the commit.

- [ ] **Step 1: Failing test** (stub `EM_IBD_P` binary, same technique as Task 13)

```python
# tests/test_tools_relatedness.py
import stat, textwrap
from pathlib import Path
from dartr_tools.tools import relatedness

def test_relatedness_local(monkeypatch, tmp_path):
    prog = tmp_path / "prog"; prog.mkdir()
    b = prog / "EM_IBD_P"
    b.write_text("#!/bin/sh\n: > relatedness.out\necho done\n")
    b.chmod(b.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(prog))
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path / "work"))
    wd = tmp_path / "work" / "s"; wd.mkdir(parents=True)
    for ext in ("bed", "bim", "fam"):
        (wd / f"in.{ext}").write_text("x\n")
    out = relatedness.run_relatedness("s", "in")
    assert (wd / "relatedness.out").is_file()
```

- [ ] **Step 2: Run — expect FAIL.** `uv run pytest tests/test_tools_relatedness.py -v`

- [ ] **Step 3: Implement**

```python
# src/dartr_tools/tools/relatedness.py
from ..session import workdir
from ..sandbox import resolve_input
from ..registry import resolve
from ..config import settings
from ..executor import run_local, run_remote
from ..provenance import record

def run_relatedness(session_id: str, plink: str, heavy: bool = False) -> dict:
    """Estimate pairwise relatedness (EMIBD9) on a PLINK bfile prefix."""
    wd = workdir(session_id)
    bed = resolve_input(f"{plink}.bed", wd)
    binary = resolve("emibd9")
    argv = [str(binary), "--bfile", str(wd / plink)]
    if heavy:
        r = run_remote(argv, remote_cwd=f"/mnt/local/output/{session_id}", host=settings().luism01_host,
                       stage_in=[wd / f"{plink}.{e}" for e in ("bed", "bim", "fam")],
                       stage_out_dir=wd, timeout=settings().remote_timeout)
    else:
        r = run_local(argv, cwd=wd, timeout=settings().local_timeout)
    outputs = ["relatedness.out"]
    record(wd, "run_relatedness", {"plink": plink, "heavy": heavy}, [bed], [wd / o for o in outputs], 0)
    return {"outputs": outputs}
```

Register in `tools/__init__.py`.

- [ ] **Step 4: Run — expect PASS.** `uv run pytest tests/test_tools_relatedness.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/tools/relatedness.py src/dartr_tools/tools/__init__.py tests/test_tools_relatedness.py
git commit -m "feat: run_relatedness tool (EMIBD9)"
```

---

## Task 15: `estimate_ne` tool

**Files:**
- Create: `src/dartr_tools/tools/ne.py`; **Modify:** `tools/__init__.py`
- Test: `tests/test_tools_ne.py`

**Interfaces:**
- Consumes: `rbridge.call_gl("gl.LDNe", ...)`, `registry.resolve("ne2")` (passed to R as `neest_path`).
- Produces: `estimate_ne(session_id, rds)` → `{"outputs": ["ne.rds"]}`. `gl.LDNe` shells out to NeEstimator/`Ne2-1M`; its path comes from the registry, keeping the binary pinned.

- [ ] **Step 1: Failing test**

```python
# tests/test_tools_ne.py
import shutil, pytest
from dartr_tools.tools import io, ne

pytestmark = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")

def test_ne(monkeypatch, tmp_path, tiny_vcf):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(tiny_vcf.parent))  # wherever Ne2-1M lives in the env
    io.read_vcf("s", str(tiny_vcf))
    out = ne.estimate_ne("s", "gl.rds")
    assert out["outputs"] == ["ne.rds"]
```

- [ ] **Step 2: Run — expect FAIL/SKIP.** `uv run pytest tests/test_tools_ne.py -v`

- [ ] **Step 3: Implement**

```python
# src/dartr_tools/tools/ne.py
from ..session import workdir
from ..sandbox import resolve_input
from ..registry import resolve, RegistryError
from ..rbridge import call_gl
from ..provenance import record

def estimate_ne(session_id: str, rds: str) -> dict:
    """Estimate effective population size (LD method) via gl.LDNe / NeEstimator."""
    wd = workdir(session_id); rin = resolve_input(rds, wd)
    try:
        neest = str(resolve("ne2"))
    except RegistryError:
        neest = ""  # let dartRverse fall back to its own discovery
    params = {"rds": str(rin), "out": "ne", "neest_path": neest}
    res = call_gl("gl.LDNe", params, wd)
    record(wd, "estimate_ne", {"rds": str(rin)}, [rin], [wd / o for o in res["outputs"]], 0)
    return res
```

Register in `tools/__init__.py`.

- [ ] **Step 4: Run.** `uv run pytest tests/test_tools_ne.py -v` (PASS where NeEstimator+R present; SKIP otherwise)

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/tools/ne.py src/dartr_tools/tools/__init__.py tests/test_tools_ne.py
git commit -m "feat: estimate_ne tool (gl.LDNe)"
```

---

## Task 16: Guardrail integration — dry-run + confirm gate

Thread a uniform `dry_run` through the tools and mark expensive tools so a host confirm-gate can intercept.

**Files:**
- Modify: every `tools/*.py` (add `dry_run: bool = False`, pass to `call_gl` / `run_local` / `run_remote`); `tools/__init__.py` (a `EXPENSIVE` set)
- Test: `tests/test_guardrails.py`

**Interfaces:**
- Produces: each tool accepts `dry_run` (returns the command(s) it *would* run without executing); `tools.EXPENSIVE = {"run_admixture", "run_relatedness"}` for the host to require confirmation.

- [ ] **Step 1: Failing test**

```python
# tests/test_guardrails.py
from dartr_tools import tools
from dartr_tools.tools import admixture

def test_expensive_set():
    assert {"run_admixture", "run_relatedness"} <= tools.EXPENSIVE

def test_admixture_dry_run(monkeypatch, tmp_path):
    import stat
    prog = tmp_path / "prog"; prog.mkdir()
    b = prog / "admixture"; b.write_text("#!/bin/sh\nexit 0\n"); b.chmod(b.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(prog))
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path / "w"))
    wd = tmp_path / "w" / "s"; wd.mkdir(parents=True)
    for e in ("bed", "bim", "fam"):
        (wd / f"in.{e}").write_text("x\n")
    out = admixture.run_admixture("s", "in", k_min=2, k_max=2, dry_run=True)
    assert out["dry_run"] and not list(wd.glob("*.Q"))
```

- [ ] **Step 2: Run — expect FAIL.** `uv run pytest tests/test_guardrails.py -v`

- [ ] **Step 3: Implement** — add `dry_run` param to each tool signature and pass it through to the executor/bridge calls; when `dry_run`, return `{"dry_run": [commands], "outputs": []}` and skip `record`. Add to `tools/__init__.py`:

```python
EXPENSIVE = {"run_admixture", "run_relatedness"}
```

(For `run_admixture`, collect each `r.stdout` from `run_local(..., dry_run=True)` into a `dry_run` list and return early before parsing CV.)

- [ ] **Step 4: Run — expect PASS.** `uv run pytest tests/test_guardrails.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/dartr_tools/tools/ tests/test_guardrails.py
git commit -m "feat: dry-run mode + expensive-tool set for confirm gate"
```

---

## Task 17: Full-suite check + MCP registration docs

**Files:**
- Modify: `README.md` (registration snippets); Create: `docs/registration.md`
- Test: run the whole suite

- [ ] **Step 1: Run the full suite**

Run: `uv run pytest -v`
Expected: all PASS or SKIP (R/luism01-gated). Zero failures.

- [ ] **Step 2: Write registration docs**

```markdown
# docs/registration.md
## Claude Code
Add to `~/.claude.json` (or project `.mcp.json`):
{ "mcpServers": { "dartr-tools": { "command": "uv", "args": ["run", "--directory", "/Users/mijangos/projects/dartr-tools", "dartr-tools"] } } }

## opencode
Add to `openscience.json` / `opencode.json` `mcp` block with the same command/args.

## Environment
- DARTR_DATA_DIRS: colon-separated dirs the agent may read inputs from (e.g. ~/sources:~/potorous)
- DARTR_PROGRAMS_DIR: defaults to ~/programs
- DARTR_LUISM01_HOST: ssh alias, defaults to luism01
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/registration.md
git commit -m "docs: MCP registration for Claude Code + opencode"
```

- [ ] **Step 4: Push**

```bash
git push
```

---

## Self-Review

**Spec coverage:** architecture (Tasks 1,6,8,12) ✓; 9-tool v1 catalog — read_vcf/convert (9), filter_snps (10), report_diversity/report_fst/pcoa (11), run_admixture (13), run_relatedness (14), estimate_ne (15) ✓; execution/routing incl. session workdir (3), local (6) + remote (12) + provenance (7) ✓; guardrails — no-shell (by construction), injection-proof R runner (8), path sandbox (4), read-only inputs + bounds (4), env scrub (6), confirm-gate/dry-run (16) ✓; testing — fixture VCF + real-impl tests with R/luism01 skips (8, throughout) ✓.

**Placeholder scan:** No "TBD/implement later". The one flagged unknown (EMIBD9 dartRverse wrapper) is spec open-question §8.1 and is called out in Task 14 with a concrete fallback, not left blank.

**Type consistency:** `call_gl(fn, params, workdir, timeout, dry_run)` used consistently (Tasks 8–11,15); `run_local(argv, cwd, timeout, dry_run)` / `run_remote(argv, remote_cwd, host, stage_in, stage_out_dir, timeout, dry_run)` consistent (Tasks 6,12–14); every tool returns `{"outputs": [...]}` (plus `cv` for admixture, `dry_run` when dry). `resolve_input/resolve_output` signatures stable (Task 4 onward).
