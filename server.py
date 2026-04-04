from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from codex_everything_mcp.sdk import EverythingClient, SORT_VALUES


server = FastMCP(
    name="everythingLocal",
    instructions=(
        "Use this server for very fast Windows file and folder lookup powered by the "
        "Everything index. Prefer this when you need absolute paths or quick filename/path search."
    ),
)

_client: EverythingClient | None = None


def _get_client() -> EverythingClient:
    global _client
    if _client is None:
        _client = EverythingClient()
    return _client


@server.tool(
    description=(
        "Search Windows files and folders using the Everything index. Returns absolute paths "
        "and item type metadata. Supports native Everything query syntax."
    )
)
def search_everything(
    query: str,
    limit: int = 20,
    offset: int = 0,
    match_path: bool = False,
    match_case: bool = False,
    whole_word: bool = False,
    regex: bool = False,
    sort: str = "name_ascending",
    kind: str = "all",
) -> dict[str, Any]:
    return _get_client().search(
        query,
        limit=limit,
        offset=offset,
        match_path=match_path,
        match_case=match_case,
        whole_word=whole_word,
        regex=regex,
        sort=sort,
        kind=kind,
    )


@server.tool(
    description=(
        "Report Everything SDK status, loaded DLL path, database state, and detected target machine."
    )
)
def everything_health() -> dict[str, Any]:
    health = _get_client().health()
    health["supported_sorts"] = sorted(SORT_VALUES)
    return health


@server.resource(
    "everything://usage",
    name="Everything MCP Usage",
    description="Usage guidance for the local Everything-backed Codex MCP server.",
    mime_type="text/markdown",
)
def usage_resource() -> str:
    return (
        "# Everything Local MCP\n\n"
        "- Use `search_everything` for fast filename or path lookup.\n"
        "- `query` accepts native Everything search syntax.\n"
        "- `kind` can be `all`, `file`, or `folder`.\n"
        "- `match_path=true` makes path segments participate in matching.\n"
        "- Run `everything_health` if queries fail to confirm the SDK and index are available.\n"
    )


if __name__ == "__main__":
    server.run()
