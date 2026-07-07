# CLAUDE.md — dartr-tools

## What this is

A Python **MCP server** (`dartr-tools`) that exposes the local population-genetics
toolkit as typed, guardrailed, agent-callable tools, consumed by both Claude Code
and opencode. It wraps:

- **`~/programs` binaries** (admixture, EM_IBD_P/EMIBD9, Ne2-1M, plink, bcftools, …)
  — see `~/.claude/CLAUDE.md` for the full inventory. **Never copy these binaries
  into this repo**; resolve them from `~/programs` via a pinned registry.
- **dartRverse functions** (`gl.read.vcf`, `gl.filter.*`, `gl2plink`, `gl.fst.pop`,
  `gl.pcoa`, `gl.report.heterozygosity`, `gl.LDNe`, …) via a stateless Rscript bridge.
  Use `library(dartRverse)` / the specific sub-package, never `library(dartR)`.

Heavy jobs route to the **luism01** DArT VM under the existing `dart-compute` skill
rules (read-only input mount, output to ephemeral `/mnt/local/output`).

## Source of truth

`SPEC.md` — architecture, the v1 tool catalog (9 tools), execution/routing, and
guardrails. Read it before implementing anything.

## Non-negotiables (from the spec)

- **No generic shell tool.** The agent may only call the defined typed tools.
- **Injection-proof:** pass args as structured data (JSON/argv), never string-interpolated
  into a shell command or R `eval`; dartRverse calls hit a fixed function allowlist.
- **Path sandbox:** inputs/outputs must resolve inside allowed roots; reject `..`
  escapes and out-pointing symlinks. Inputs are read-only; never mutate the source VCF.
- **Provenance:** every tool call appends to a per-session run manifest.

## Development

Bun is not involved — this is Python. Tooling (package manager, test runner, entry
point) is defined by the implementation plan; update this section once it lands.

## Conventions

- dartRverse function names must be confirmed against the live package NAMESPACE
  before use (the suite evolves): `green-striped-gecko/dartR.base`, `dartR.popgen`.
- Tests use real implementations against a tiny fixture VCF — no mocks.
