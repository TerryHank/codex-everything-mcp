# Codex Everything MCP

This project exposes the Everything SDK as a local MCP server for Codex.

## Tools

- `search_everything`: Search files and folders through the Everything index.
- `everything_health`: Check SDK loading, target machine, and database status.

## Local Run

```powershell
.\.venv\Scripts\python.exe .\server.py
```

## Notes

- This server is Windows-only.
- It expects the Everything desktop app/service to be running.
- Register it in your Codex global config as an MCP server that runs `python server.py`.
