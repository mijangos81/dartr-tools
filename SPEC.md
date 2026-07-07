# dartR-tools — a popgen MCP tool surface

**Status:** Draft design · 2026-07-08
**Author:** Luis Mijangos (with Claude)
**One-line:** A single MCP server that makes your local population-genetics toolkit (`~/programs` binaries + dartRverse functions) directly callable by an AI agent — the "unified scientific-tool surface" OpenScience gives molecular/ML biology, built for conservation/population genomics instead.

---

## 1. Motivation

OpenScience (an opencode fork for science) exposes ~30 external databases as agent-callable tools, plus inline scientific rendering and ML-training/cheminformatics skills. Its one real gap for our field: it does **no** population/conservation genomics — no Fst, Ne, admixture, coalescent, DArTseq, or VCF popgen.

We already own the tools that matter (the `~/programs` binaries and the dartRverse suite) but they are not agent-callable: today the assistant can only *talk about* them. This project gives the agent typed **buttons** to actually run them and chain them into a real analysis, without adopting OpenScience's fork, Atlas upsell, or ToS-risky subscription auth.

## 2. Goals / non-goals

**Goals**
- One MCP server (`dartr-tools`) consumed by **both** Claude Code and opencode from the same config.
- Typed, guardrailed tools wrapping a curated v1 slice of the local toolkit.
- Automatic routing of heavy jobs to the luism01 DArT VM under existing `dart-compute` rules.
- A reproducibility manifest for every run.

**Non-goals (v1)**
- No external-database connectors (literature/retrieval already covered by paper-search, refs-ingest, Zotero).
- No inline browser rendering (plots are returned as file paths).
- No generic shell tool. Ever.
- Not a dartRverse feature — this wraps dartRverse from outside; it does not modify the packages.

## 3. Architecture

```
          Claude Code  ┐
                       ├─ stdio ──►  dartr-tools MCP server (Python)
          opencode     ┘                     │
                                     ┌────────┼─────────┐
                                     ▼        ▼         ▼
                                 executor  Rscript   ssh luism01
                                 (local)  (dartRverse) (heavy jobs)
                                     │        │          │
                              ~/programs   R libs   /mnt/local/output
                              binaries              (dart-compute rules)
```

- **Server:** Python, `mcp` SDK. Chosen for clean subprocess handling, easy SSH (paramiko), and bioinformatics familiarity, over TypeScript (which matches the opencode idiom but makes the R bridge clunkier).
- **Executor:** shared layer that resolves the backend for each tool and runs it. Three backends:
  - **local binary** — path resolved from a pinned registry (never PATH), run as a subprocess in the session workdir.
  - **dartRverse** — a fixed R runner receives `{function, args-as-JSON}`, calls a whitelisted `gl.*` function, writes RDS/plots to the workdir, returns paths.
  - **remote** — `heavy:true` tools stage inputs to luism01, run under `dart-compute` rules (read-only input mount, output to ephemeral `/mnt/local/output`), copy results back.
- **R bridge decision:** **Rscript-per-call** (stateless, robust, ~1–2 s startup) for v1. A persistent Rserve session (faster, stateful, more fragile) is deferred until startup latency is shown to matter.

## 4. v1 tool catalog

Nine tools forming one end-to-end loop: read → filter → convert → analyse. Every handoff is a **file path** (RDS / PLINK / VCF); large data never passes through the model.

| Tool | Purpose | Backend | dartRverse fn / binary | Pkg |
|---|---|---|---|---|
| `read_vcf` | VCF → genlight RDS | dartRverse | `gl.read.vcf` | dartR.base |
| `filter_snps` | call rate / MAF / rdepth / monomorph filters | dartRverse | `gl.filter.callrate`, `gl.filter.maf`, `gl.filter.rdepth`, `gl.filter.monomorphs` | dartR.base |
| `convert` | genlight ↔ PLINK ↔ VCF | dartRverse | `gl2plink`, `gl2vcf` | dartR.base |
| `report_diversity` | Ho / He / diversity per pop | dartRverse | `gl.report.heterozygosity`, `gl.report.diversity` | dartR.base |
| `report_fst` | pairwise Fst | dartRverse | `gl.fst.pop` | dartR.base |
| `pcoa` | ordination + plot | dartRverse | `gl.pcoa`, `gl.pcoa.plot` | dartR.base |
| `run_admixture` | ADMIXTURE over a K range with CV error | local binary (+ luism01 if big) | `~/programs/admixture`; input prepped via `gl2plink` | — |
| `run_relatedness` | pairwise relatedness / kinship | local binary (+ luism01 if big) | `~/programs/EM_IBD_P` (EMIBD9) | — |
| `estimate_ne` | effective population size (LD method) | dartRverse → binary | `gl.LDNe` (wraps NeEstimator/`Ne2-1M`) | dartR.popgen |

**Demo the loop enables:** *"load this VCF, filter to call rate ≥0.95 and MAF ≥0.05, then give me Fst, a PCoA, ADMIXTURE K=2–6 with CV, and an Ne estimate."*

**Deferred to v2+ (already owned):** selection scans (`selscan`, `gl2bayescan` → `bayescan`), simulation (`slim`, `ms` → dartR.sim), demography (`stairway_plot`, `epos`), other structure engines (`gl.run.structure`, `gl.run.faststructure` — dartR.popgen), parentage (`colony`), spatial (dartR.spatial, EEMS `runeems_snps`), sex-linked (dartR.sexlinked).

## 5. Execution & routing

- **Session workdir:** `~/.dartr-tools/work/<session>/`; every tool reads inputs and writes outputs here.
- **Routing:** each tool carries a `heavy` flag (default explicit). `run_admixture` / `run_relatedness` auto-escalate to luism01 above a data-size threshold. A lock/availability check runs first, since another session may be on the shared VM.
- **Remote staging:** inputs copied to the read-only mount, job run, outputs written to `/mnt/local/output`, then copied back to the local workdir — matching the `dart-compute` skill exactly.
- **Provenance:** every call appends to a run manifest — tool, args, input file hashes, binary/package version, exit code, output paths, timestamp. This is the reproducibility record and feeds the capture-knowledge habit.

## 6. Guardrails

- **No generic shell.** The agent can only call the nine typed tools; it cannot construct an arbitrary command.
- **Injection-proof.** Args pass as structured data (JSON/argv), never interpolated into a shell string or R `eval`; dartRverse calls hit a fixed function allowlist.
- **Path sandbox.** Paths must resolve inside allowed roots (session workdir + a whitelisted data dir); `..` escapes, out-of-allowlist absolute paths, and out-pointing symlinks are rejected. Numeric params bounded (e.g. K ∈ 1–20, call rate ∈ 0–1).
- **Inputs read-only.** Originals copied in, never mutated; outputs only in the workdir (or `/mnt/local/output` remotely). The source VCF is never clobbered.
- **Resource caps.** Per-tool timeout + wall-clock limit; heavy jobs go remote. Credentials scrubbed from every subprocess env.
- **Confirm gate.** Read-only analyses (Fst, PCoA, diversity) run freely; writing outside the workdir, big remote jobs, or overwriting a result require an explicit OK (Claude Code permission-prompt shape).
- **Dry-run.** Every tool can print the exact command it *would* run without executing.

## 7. Testing

Per the repo style (real implementations, no mocks):
- A tiny fixture VCF (a few hundred SNPs, 2–3 populations) checked into `test/fixtures/`.
- One integration test per tool that runs it for real against the fixture and asserts on outputs (file exists, shape/columns, value sanity — e.g. Fst ∈ [0,1]).
- Path-sandbox and injection guards tested with adversarial inputs (`../` escapes, args containing shell/R metacharacters).
- luism01 routing tested behind a flag / skipped when the VM is unreachable.

## 8. Open questions (resolve during planning)

1. **EMIBD9 wrapper:** confirm whether a `gl.run.emibd9`-style wrapper exists on a dartR.popgen dev branch; if so, prefer it over calling `EM_IBD_P` directly.
2. **Size threshold** for auto-escalating admixture/relatedness to luism01 — needs a concrete SNP × individual rule.
3. **Config surface:** whitelisted data dirs, the luism01 host alias, and per-tool timeouts — where they live and their defaults.
4. **Project home:** bootstrap this as its own repo (via the `start-project` skill) before implementation.
