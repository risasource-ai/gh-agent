# gh-mcp

Full GitHub control as an MCP server. Every capability GitHub exposes,
available to any AI agent that speaks MCP — Claude, GPT-4, Gemini, or
your own coordinator.

## What this is

An MCP server that gives AI agents complete, first-class access to GitHub.
Not a wrapper around another library — raw GitHub API calls, clean responses,
and a module per domain so you can extend or audit any piece independently.

## What's built

| Module | Capabilities |
|---|---|
| `identity` | whoami, rate limit |
| `repos` | create, update, delete, fork, topics, branches, tags, commits |
| `files` | read, write, delete, upsert, tree, raw |
| `pulls` | create, review, merge, inline comments, reviewer requests |
| `issues` | create, assign, label, milestone, comments |

## Coming next

- `actions` — trigger workflows, check run status, manage secrets
- `releases` — create releases, upload assets
- `discussions` — GraphQL-based discussions (create, reply, answer)
- `orgs` — members, teams, permissions
- `search` — cross-repo code, issue, and user search

## Setup

```bash
# requires Python 3.11+
pip install uv
uv sync
cp .env.example .env
# add your GITHUB_TOKEN to .env
```

GitHub PAT scopes needed: `repo`, `read:org`, `read:user`
Create at: github.com → Settings → Developer settings → Personal access tokens

## Run

```bash
# development — opens MCP inspector in browser
mcp dev server.py

# stdio — for Claude Desktop or any stdio MCP client
mcp run server.py

# HTTP — for remote agents
python server.py --transport http --port 8000
```

## Connect to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "python",
      "args": ["/path/to/gh-mcp/server.py"],
      "env": {
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Architecture

```
server.py              ← FastMCP entry point, mounts all modules
github/
  client.py            ← raw httpx REST + GraphQL, shared auth
  repos.py             ← repo, branch, tag, commit tools
  files.py             ← file read/write tools
  pulls.py             ← PR and review tools
  issues.py            ← issue and label tools
  ...                  ← one file per domain
```

Each module has a `register(mcp, client, owner)` function.
Adding a new capability = add a new module + one line in server.py.

## Use without MCP (plain Python)

```python
from github.client import GitHubClient

client = GitHubClient(token="your_pat")
repos = client.rest("GET", "/user/repos")
```

The client is just httpx under the hood — no framework dependency.
