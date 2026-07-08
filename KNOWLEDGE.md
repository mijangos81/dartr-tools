[//]: # (vault-link: ~/projects)

> Tracker: [[projects#dartr-tools]]

# Knowledge — dartr-tools

Captured items for this project. Five sections, append-only. See [[Learnings]], [[Problems solved]], [[Ideas]], [[Tips]], [[Decisions]] for the transversal view.

## Learnings

- **2026-07-08** — `gl.run.EMIBD9` lives in **dartR.captive** (not dartR.popgen/base) and wraps the whole EMIBD9 pipeline: writes `EMIBD9_Gen.dat` + `MyData.par`, runs `./EM_IBD_P INP:MyData.par`, and parses the `.ibd9` output into a square `$rel` relatedness matrix (deterministic at `ISeed=42`; self-relatedness diag=0.5). `EM_IBD_P` is parameter-file-driven (`MyData.par`), NOT `--bfile` — so route agent relatedness through `gl.run.EMIBD9` via the R bridge (like estimate_ne→gl.LDNe) with a genlight RDS + `emibd9.path`=folder + `plot.out=FALSE`, not the raw binary with PLINK input. #dartRverse #dartR #relatedness #mcp #r

## Problems solved

- **2026-07-08** — R bridge JSON corrupted when a dartRverse fn shells out to an external binary (gl.LDNe → NeEstimator/Ne2-1M): the subprocess writes to fd 1, which R's `sink()` does NOT capture, so its progress text leaked onto stdout and broke `JSON.parse`. Fix: the Rscript runner writes result JSON to a response file (`workdir/_rresp.json`), unlinked before each run so a 0-exit-without-write can't return a stale prior result; the Python side reads the file, never stdout. #mcp #dartRverse #r #subprocess #gotcha
  - links: https://github.com/mijangos81/dartr-tools/pull/1

## Ideas

## Tips

## Decisions
