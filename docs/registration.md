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

## Environment variables

The server reads the following environment variables:

| Variable | Purpose | Default | Example |
|---|---|---|---|
| `DARTR_DATA_DIRS` | Colon-separated list of directories the agent may read inputs from | (none; cwd-relative paths permitted) | `~/sources:~/potorous` |
| `DARTR_PROGRAMS_DIR` | Directory containing the local tool binaries (admixture, EM_IBD_P, bcftools, …) | `~/programs` | `~/programs` |
| `DARTR_LUISM01_HOST` | SSH host alias for the remote DArT compute VM (luism01) | `luism01` | `luism01` |

To restrict the agent to specific data roots, set `DARTR_DATA_DIRS` in the shell environment before starting Claude Code or opencode.
