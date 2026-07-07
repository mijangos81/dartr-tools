# dartr-tools

A single MCP server that makes the local population-genetics toolkit — the `~/programs` binaries and the dartRverse suite — directly callable by an AI agent, from both Claude Code and opencode.

It closes the one real gap that science-focused agents (e.g. OpenScience) leave for conservation/population genomics: a **unified, guardrailed scientific-tool surface** for our field, without adopting a fork, a managed-wallet upsell, or ToS-risky subscription auth.

See [SPEC.md](SPEC.md) for the full design (architecture, v1 tool catalog, execution/routing, guardrails, testing).

## Status

Design stage. No implementation yet — the next step is an implementation plan derived from the spec.

## What it will do (v1)

Nine typed tools forming one end-to-end popgen loop, chainable by the agent:

`read_vcf` → `filter_snps` → `convert` → `report_diversity` · `report_fst` · `pcoa` · `run_admixture` · `run_relatedness` · `estimate_ne`

Heavy jobs (large ADMIXTURE / relatedness runs) route automatically to the luism01 DArT VM under existing `dart-compute` rules. Every run writes a reproducibility manifest.

## Layout

| Path | Purpose |
|---|---|
| `SPEC.md` | Design document — the source of truth for v1. |
| `KNOWLEDGE.md` | Learnings, problems solved, ideas captured during the build. |

Further structure (server package, tool registry, tests) is defined by the implementation plan.

## Knowledge

See `KNOWLEDGE.md` for captured learnings, problems solved, and decisions.
