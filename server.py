"""
server.py

gh-mcp: Full GitHub control as an MCP server.

Every GitHub capability is registered as an MCP tool here.
Supports stdio (Claude Desktop, local agents) and HTTP (remote agents).

Usage:
    mcp dev server.py                   # development with inspector
    mcp run server.py                   # stdio mode
    python server.py --transport http   # HTTP mode

Environment:
    GITHUB_TOKEN   required  GitHub Personal Access Token
    GITHUB_OWNER   optional  defaults to the authenticated user's login
"""

import os
import sys
import logging
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("gh-mcp")


def create_server() -> FastMCP:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        log.error("GITHUB_TOKEN is not set. Create one at github.com/settings/tokens")
        sys.exit(1)

    from github.client import GitHubClient
    client = GitHubClient(token=token)

    # resolve owner — use env override or fall back to authenticated user
    owner = os.getenv("GITHUB_OWNER", "")
    if not owner:
        try:
            me = client.whoami()
            owner = me["login"]
            log.info(f"authenticated as {owner}")
        except Exception as e:
            log.error(f"GitHub auth failed: {e}")
            sys.exit(1)

    mcp = FastMCP(
        "gh-mcp",
        instructions=f"""
You have full control over the GitHub account belonging to {owner}.
You can read and write to all repositories, manage pull requests,
issues, releases, actions, and more.

Always verify what exists before creating or modifying things.
For destructive operations (delete repo, force push), state what
you're about to do before doing it.
""".strip(),
    )

    # register tools from each module
    _register_identity(mcp, client, owner)

    from github import repos, files, pulls, issues
    repos.register(mcp, client, owner)
    files.register(mcp, client, owner)
    pulls.register(mcp, client, owner)
    issues.register(mcp, client, owner)

    # these modules will be added next
    # from github import actions, releases, discussions, orgs, search
    # actions.register(mcp, client, owner)
    # releases.register(mcp, client, owner)
    # discussions.register(mcp, client, owner)
    # orgs.register(mcp, client, owner)
    # search.register(mcp, client, owner)

    log.info(f"gh-mcp ready — {owner}")
    return mcp


def _register_identity(mcp: FastMCP, client, owner: str):
    """Register the identity/account tools."""

    from github.client import GitHubError

    @mcp.tool()
    def whoami() -> dict:
        """
        Get information about the authenticated GitHub account.
        Call this first to understand whose account you're working with.
        """
        try:
            me = client.whoami()
            return {
                "login": me["login"],
                "name": me.get("name"),
                "email": me.get("email"),
                "public_repos": me.get("public_repos"),
                "private_repos": me.get("total_private_repos"),
                "followers": me.get("followers"),
                "url": me.get("html_url"),
                "bio": me.get("bio"),
            }
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def get_rate_limit() -> dict:
        """
        Check the current GitHub API rate limit status.
        Useful before running bulk operations.
        """
        try:
            result = client.rest("GET", "/rate_limit")
            core = result["resources"]["core"]
            search = result["resources"]["search"]
            graphql = result["resources"].get("graphql", {})
            return {
                "core": {
                    "limit": core["limit"],
                    "remaining": core["remaining"],
                    "reset_at": core["reset"],
                },
                "search": {
                    "limit": search["limit"],
                    "remaining": search["remaining"],
                },
                "graphql": {
                    "limit": graphql.get("limit"),
                    "remaining": graphql.get("remaining"),
                },
            }
        except GitHubError as e:
            return e.to_dict()


# ── entry point ───────────────────────────────────────────────────────

mcp = create_server()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="gh-mcp GitHub MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport to use (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)",
    )
    args = parser.parse_args()

    if args.transport == "http":
        log.info(f"starting HTTP server on port {args.port}")
        mcp.run(transport="streamable-http", port=args.port)
    else:
        log.info("starting stdio server")
        mcp.run(transport="stdio")
