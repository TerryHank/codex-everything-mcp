# Codex Everything MCP

This project exposes the Everything SDK as a local MCP server for Codex.

It is packaged as a Python MCP server with both a console entry point and a
checkout-compatible `server.py` shim.

## Tools

- `search_everything`: Search files and folders through the Everything index.
- `everything_health`: Check SDK loading, target machine, and database status.

## Requirements

- Windows.
- Python 3.11+.
- Everything desktop app or service running.
- Everything SDK DLL available locally. Set `EVERYTHING_SDK_DLL` to the exact
  DLL path, or set `EVERYTHING_SDK_ROOT` to a folder containing `dll/`.

## Run From Git

```powershell
uvx --from git+https://github.com/TerryHank/codex-everything-mcp codex-everything-mcp
```

## Local Development

```powershell
uv sync
uv run codex-everything-mcp
```

For existing local Codex registrations that run the checkout directly:

```powershell
uv run python .\server.py
```

## Codex MCP Config Example

```toml
[mcp_servers.everything_local]
command = "uvx"
args = ["--from", "git+https://github.com/TerryHank/codex-everything-mcp", "codex-everything-mcp"]

[mcp_servers.everything_local.env]
EVERYTHING_SDK_DLL = "C:\\path\\to\\Everything64.dll"
```
