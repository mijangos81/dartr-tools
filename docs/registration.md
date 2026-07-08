# MCP Server Registration

The `dartr-tools` MCP server exposes population-genetics tools (9 typed functions) for use by Claude Code and opencode agents.

## Registration with Claude Code

Add the server to your `~/.claude.json` or project `.mcp.json`:

```json
{
  "mcpServers": {
    "dartr-tools": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/mijangos/projects/dartr-tools", "dartr-tools"]
    }
  }
}
```

## Registration with opencode

Add to the `mcp` block in `opencode.json` or `openscience.json` (same command/args):

```json
{
  "mcp": {
    "dartr-tools": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/mijangos/projects/dartr-tools", "dartr-tools"]
    }
  }
}
```

## Confirm gate

The server exposes `tools.EXPENSIVE = {run_admixture, run_relatedness}` — the set of
tools that shell out to potentially long-running external binaries (and may route to
the remote `luism01` VM). Hosts SHOULD require explicit user confirmation before
invoking any tool in this set, and before any tool call that would overwrite an
existing output file.

This confirmation gate is currently a **host-side responsibility**: the server does
not itself block or prompt for these calls, it only advertises which tools warrant
a confirmation step via `tools.EXPENSIVE`.

## Environment variables

The server reads the following environment variables:

| Variable | Purpose | Default | Example |
|---|---|---|---|
| `DARTR_DATA_DIRS` | Colon-separated list of directories the agent may read inputs from | (none; cwd-relative paths permitted) | `~/sources:~/potorous` |
| `DARTR_PROGRAMS_DIR` | Directory containing the local tool binaries (admixture, EM_IBD_P, bcftools, …) | `~/programs` | `~/programs` |
| `DARTR_LUISM01_HOST` | SSH host alias for the remote DArT compute VM (luism01) | `luism01` | `luism01` |

To restrict the agent to specific data roots, set `DARTR_DATA_DIRS` in the shell environment before starting Claude Code or opencode.
