# run_relatedness → gl.run.EMIBD9 Rework — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the stub-shaped `run_relatedness` (PLINK `--bfile` + raw `EM_IBD_P`, which is inert because EM_IBD_P is `MyData.par`-driven) with a real implementation that routes through `gl.run.EMIBD9` (dartR.captive) via the existing R bridge — mirroring `estimate_ne` → `gl.LDNe`.

**Architecture:** Add a `gl.run.EMIBD9` branch to the fixed-dispatch R runner and to `rbridge.ALLOW`; rewrite `run_relatedness` to take a genlight **RDS** (dropping the PLINK plumbing), call the wrapper with `emibd9.path` server-sourced from `~/programs` and `plot.out=FALSE`, and return the pairwise relatedness matrix as CSV. Validated locally: 12×12 matrix, diagonal 0.5 (self), off-diagonal r ∈ [0.001, 0.388].

**Tech Stack:** Python (FastMCP), the existing `rbridge` response-file mechanism, `gl.run.EMIBD9` (dartR.captive), `pytest`.

**Context:** This is a follow-up to PR #1 (branch `feat/v1-implementation`). Land it either as additional commits on that branch or a fresh branch off it. `dartR.captive` is installed and `gl.run.EMIBD9` resolves after `library(dartRverse)`; the binary `~/programs/EM_IBD_P` runs (validated).

## Global Constraints

- Injection-proof: `fn` dispatched via the runner's fixed `if/else if`; params as JSON data; `rbridge.ALLOW` mirrors the runner's branch set.
- `emibd9_path` is SERVER-SOURCED (`settings().programs_dir`), never an agent tool param — it flows to `gl.run.EMIBD9`'s `emibd9.path`, which is the **folder** containing `EM_IBD_P`.
- `plot.out = FALSE` always (headless `Rscript` has no graphics device).
- Input paths sandbox-resolved via `resolve_input`; provenance recorded on success; `dry_run` returns `{"outputs": [], "dry_run": [...]}` and skips `record`.
- Tests use real implementations against the fixture; skip (not fail) when `Rscript` or `EM_IBD_P` is absent.
- EMIBD9 truncates individual IDs > 20 chars and forbids spaces / `/` — document in the tool docstring.

---

## File Structure

```
src/dartr_tools/r/runner.R      + gl.run.EMIBD9 branch; ensure dartR.captive loaded
src/dartr_tools/rbridge.py      + "gl.run.EMIBD9" in ALLOW
src/dartr_tools/tools/relatedness.py   rewritten: RDS in, wrapper call, CSV out (no PLINK/registry/executor)
tests/test_rbridge.py           + gl.run.EMIBD9 roundtrip test
tests/test_tools_relatedness.py rewritten: matrix structural + determinism + path-escape tests
```

`tools/__init__.py` needs no change (registration is by reference; `run_relatedness` stays in `EXPENSIVE` — EMIBD9 is O(n²) pairwise).

---

## Task 1: Add `gl.run.EMIBD9` to the R bridge

**Files:**
- Modify: `src/dartr_tools/r/runner.R`, `src/dartr_tools/rbridge.py`
- Test: `tests/test_rbridge.py`

**Interfaces:**
- Produces: an allowlisted `gl.run.EMIBD9` gl-function reachable via `rbridge.call_gl("gl.run.EMIBD9", {rds, emibd9_path, iseed, inbreed}, wd)`, which writes `relatedness.csv` (the `$rel` matrix) into the workdir and returns `{"outputs": ["relatedness.csv"]}`.

- [ ] **Step 1: Add the runner branch.** In `src/dartr_tools/r/runner.R`, ensure dartR.captive is available (add `suppressWarnings(suppressMessages(library(dartR.captive)))` near the top library loads), and add this branch to the `if/else if` chain (before the final `else { stop(...) }`):

```r
} else if (fn == "gl.run.EMIBD9") {
  gl  <- readRDS(p$rds)
  res <- gl.run.EMIBD9(gl, emibd9.path = p$emibd9_path, plot.out = FALSE,
                       ISeed = p$iseed, Inbreed = isTRUE(p$inbreed), verbose = 0)
  out <- file.path(outdir, "relatedness.csv")
  write.csv(res$rel, out)
  emit(c("relatedness.csv"))
```

- [ ] **Step 2: Add to the Python allowlist.** In `src/dartr_tools/rbridge.py`, add `"gl.run.EMIBD9"` to the `ALLOW` set.

- [ ] **Step 3: Write the failing test** (append to `tests/test_rbridge.py`):

```python
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
```

- [ ] **Step 4: Run.** `uv run pytest tests/test_rbridge.py -v` — new test PASS (or SKIP if `EM_IBD_P` absent), existing rbridge tests still PASS.

- [ ] **Step 5: Commit.**

```bash
git add src/dartr_tools/r/runner.R src/dartr_tools/rbridge.py tests/test_rbridge.py
git commit -m "feat: add gl.run.EMIBD9 (dartR.captive) to the R bridge"
```

---

## Task 2: Rewrite `run_relatedness` onto the wrapper

**Files:**
- Rewrite: `src/dartr_tools/tools/relatedness.py`
- Rewrite: `tests/test_tools_relatedness.py`

**Interfaces:**
- Consumes: `rbridge.call_gl("gl.run.EMIBD9", ...)` (Task 1), `session.workdir`, `sandbox.resolve_input`, `config.settings`, `provenance.record`.
- Produces: `run_relatedness(session_id, rds, iseed=42, inbreed=False, dry_run=False)` → `{"outputs": ["relatedness.csv"]}` (or `{"outputs": [], "dry_run": [...]}`).

- [ ] **Step 1: Write the failing tests** — replace the whole body of `tests/test_tools_relatedness.py`:

```python
import shutil, csv, statistics, pytest
from pathlib import Path
from dartr_tools.tools import io, relatedness
from dartr_tools import sandbox

_HAVE = shutil.which("Rscript") is not None and (Path.home()/"programs"/"EM_IBD_P").exists()
real = pytest.mark.skipif(not _HAVE, reason="Rscript or EM_IBD_P not available")

def _cells(path):
    with open(path) as fh:
        rows = list(csv.reader(fh))
    body = rows[1:]                      # drop header
    return [[c for c in r[1:]] for r in body]   # drop rowname col

def _prep(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path))
    monkeypatch.setenv("DARTR_DATA_DIRS", str(tiny_vcf.parent))
    monkeypatch.setenv("DARTR_PROGRAMS_DIR", str(Path.home()/"programs"))
    io.read_vcf("s", str(tiny_vcf), metafile=str(tiny_meta))

@real
def test_relatedness_matrix(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    _prep(monkeypatch, tmp_path, tiny_vcf, tiny_meta)
    out = relatedness.run_relatedness("s", "gl.rds")
    assert out["outputs"] == ["relatedness.csv"]
    cells = _cells(tmp_path/"s"/"relatedness.csv")
    n = len(cells)
    assert n == 12 and all(len(r) == n for r in cells)                      # square 12x12
    nums = [float(c) for r in cells for c in r if c not in ("", "NA")]
    assert nums and all(0.0 <= v <= 1.0 for v in nums)                      # r in [0,1]
    diag = [float(cells[i][i]) for i in range(n) if cells[i][i] not in ("", "NA")]
    assert abs(statistics.mean(diag) - 0.5) < 0.05                          # self ~ 0.5

@real
def test_relatedness_deterministic(monkeypatch, tmp_path, tiny_vcf, tiny_meta):
    _prep(monkeypatch, tmp_path, tiny_vcf, tiny_meta)
    relatedness.run_relatedness("s", "gl.rds")
    first = (tmp_path/"s"/"relatedness.csv").read_text()
    relatedness.run_relatedness("s", "gl.rds")            # ISeed=42 fixed
    assert (tmp_path/"s"/"relatedness.csv").read_text() == first

def test_relatedness_rejects_path_escape(monkeypatch, tmp_path):
    monkeypatch.setenv("DARTR_WORK_ROOT", str(tmp_path/"work"))
    with pytest.raises(sandbox.SandboxError):
        relatedness.run_relatedness("s", "../evil.rds")
```

- [ ] **Step 2: Run to verify failure.** `uv run pytest tests/test_tools_relatedness.py -v` — FAIL (old `run_relatedness` signature/behaviour).

- [ ] **Step 3: Rewrite the implementation** — replace the whole body of `src/dartr_tools/tools/relatedness.py`:

```python
from ..session import workdir
from ..sandbox import resolve_input
from ..config import settings
from ..rbridge import call_gl
from ..provenance import record

def run_relatedness(session_id: str, rds: str, iseed: int = 42, inbreed: bool = False,
                    dry_run: bool = False) -> dict:
    """Estimate pairwise relatedness with EMIBD9 (Wang 2022) via gl.run.EMIBD9 (dartR.captive).

    Input is a genlight RDS; returns a square pairwise relatedness matrix as `relatedness.csv`
    (deterministic given `iseed`). Note: EMIBD9 truncates individual IDs to 20 characters and
    forbids spaces / '/', so keep sample IDs short and unique.
    """
    wd = workdir(session_id)
    rin = resolve_input(rds, wd)
    params = {"rds": str(rin), "emibd9_path": str(settings().programs_dir),
              "iseed": iseed, "inbreed": inbreed}
    res = call_gl("gl.run.EMIBD9", params, wd, dry_run=dry_run)
    if dry_run:
        return res
    record(wd, "run_relatedness", {"rds": str(rin), "iseed": iseed, "inbreed": inbreed},
           [rin], [wd / o for o in res["outputs"]], 0)
    return res
```

- [ ] **Step 4: Run to verify pass.** `uv run pytest tests/test_tools_relatedness.py -v` — matrix + determinism tests PASS (or SKIP without `EM_IBD_P`), path-escape PASS. Then `uv run pytest -q` — whole suite green (the old stub-binary `run_admixture` test is unaffected; `run_relatedness` no longer uses the registry/executor).

- [ ] **Step 5: Commit.**

```bash
git add src/dartr_tools/tools/relatedness.py tests/test_tools_relatedness.py
git commit -m "feat: run_relatedness via gl.run.EMIBD9 (real relatedness matrix, RDS in / CSV out)"
```

---

## Self-Review

**Spec coverage:** the reframed request maps cleanly — bridge wiring (Task 1) + tool rewrite taking a genlight RDS with server-sourced `emibd9_path` and `plot.out=FALSE` (Task 2); correctness oracle = structural + determinism assertions (diag ≈ 0.5, r ∈ [0,1], byte-identical re-run at fixed seed); ID-length caveat documented in the docstring.

**Placeholder scan:** none — full runner branch, full tool body, full test bodies given.

**Type consistency:** `call_gl(fn, params, wd, dry_run=...)` matches the existing bridge signature; `run_relatedness(session_id, rds, iseed, inbreed, dry_run)` returns `{"outputs": [...]}` like every sibling tool; `resolve_input` usage matches the established pattern.

**Open decision (carry to implementation):** the matrix test asserts structure + self≈0.5, not values against a *known pedigree*. If a captive dataset with known parent–offspring/unrelated pairs is available, add an oracle test asserting PO r ≈ 0.5 / unrelated ≈ 0 — the strongest "correct" check. Left as a follow-up so the rework isn't blocked on sourcing that dataset.
```
