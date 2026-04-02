# gh-mcp

Full GitHub control as an MCP server. Give any AI agent complete,
first-class access to a GitHub account — repos, files, branches, pull
requests, issues, Actions, releases, and search.

---

## Contents

- [What this is](#what-this-is)
- [Architecture](#architecture)
- [Setup](#setup)
- [Running the server](#running-the-server)
- [Connecting to Claude Desktop](#connecting-to-claude-desktop)
- [Tool reference](#tool-reference)
  - [Identity](#identity)
  - [Repos](#repos)
  - [Files](#files)
  - [Pull Requests](#pull-requests)
  - [Issues](#issues)
  - [Actions](#actions)
  - [Releases](#releases)
  - [Search](#search)
- [Error handling](#error-handling)
- [Rate limits](#rate-limits)
- [Security](#security)
- [Running tests](#running-tests)
- [Adding a new module](#adding-a-new-module)

---

## What this is

An MCP server that gives AI agents the same GitHub access a human developer has
through the web UI — but via structured tool calls, not a browser.

The agent can:
- Read any repo, file, branch, commit, issue, PR, or workflow it has access to
- Create and modify repos, files, branches, PRs, issues, releases
- Trigger and monitor GitHub Actions workflows
- Search code, repos, issues, and commits across GitHub

The token stays on your machine. It is never sent to any AI model. The model
sees only the results of tool calls — not credentials.

---

## Architecture

```
server.py              ← FastMCP entry point, mounts all modules
github/
  client.py            ← raw httpx REST + GraphQL, shared auth
  repos.py             ← repo, branch, tag, commit tools
  files.py             ← file read/write tools
  pulls.py             ← PR, review, inline comment tools
  issues.py            ← issue, label, milestone, comment tools
  actions.py           ← workflow, run, job, secret, artifact tools
  releases.py          ← release and asset tools
  search.py            ← code, repo, issue, commit, user search
tests/
  conftest.py          ← shared MockClient fixture
  test_client.py
  test_repos.py
  test_files.py
  test_pulls.py
  test_issues.py
  test_actions.py
  test_releases.py
  test_search.py
docs/
  README.md            ← this file
```

Each module has a `register(mcp, client, owner)` function.
Adding a new capability = add a new module + one line in `server.py`.

The client exposes three methods used by every module:

| Method | Use |
|---|---|
| `client.rest(method, path, params, body)` | Any REST call |
| `client.rest_raw(method, path, accept)` | Raw text responses (diffs, patches) |
| `client.paginate(path, params, limit)` | Auto-paginated list endpoints |
| `client.graphql(query, variables)` | GraphQL (Projects v2, Discussions) |

---

## Setup

**Requirements:** Python 3.11+

```bash
pip install uv
uv sync
cp .env.example .env
```

Edit `.env`:

```bash
# Required
GITHUB_TOKEN=your_personal_access_token

# Optional — defaults to the authenticated user's login
GITHUB_OWNER=your_github_username
```

**GitHub PAT scopes needed:**

| Scope | Why |
|---|---|
| `repo` | Read/write all repo content |
| `read:user` | Resolve authenticated username |
| `delete_repo` | Only if you want the agent to delete repos |
| `workflow` | Only if you want the agent to trigger Actions |

Create at: github.com → Settings → Developer settings → Personal access tokens → Tokens (classic)

---

## Running the server

```bash
# Development — opens MCP inspector in browser at localhost:5173
mcp dev server.py

# stdio — for Claude Desktop or any stdio MCP client
mcp run server.py

# HTTP — for remote agents or multi-client setups
python server.py --transport http --port 8000
```

---

## Connecting to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`
(Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "github": {
      "command": "python",
      "args": ["/absolute/path/to/gh-mcp/server.py"],
      "env": {
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

Restart Claude Desktop. You should see the GitHub tools available.

---

## Tool reference

### Identity

#### `whoami`
Returns info about the authenticated account. Call this first.

```
→ login, name, email, public_repos, private_repos, followers, url, bio
```

#### `get_rate_limit`
Check remaining API quota before bulk operations.
Core limit: 5000 req/hour. Search: 30 req/min (separate limit).

```
→ core.remaining, core.limit, core.reset_at
→ search.remaining, graphql.remaining
```

---

### Repos

#### `list_repos(visibility, sort, limit)`
List all repos in the account, including private ones.

- `visibility`: `"all"` | `"public"` | `"private"` (default `"all"`)
- `sort`: `"updated"` | `"created"` | `"pushed"` | `"full_name"`
- `limit`: max results (default 50)

#### `get_repo(repo)`
Full details for one repo: stars, forks, language, issues count, clone URL.

#### `create_repo(name, description, private, auto_init, gitignore_template, license_template)`
Create a new repo.

- `auto_init`: creates an initial commit with README (default `true`)
- `gitignore_template`: e.g. `"Python"`, `"Node"`, `"Go"`
- `license_template`: e.g. `"mit"`, `"apache-2.0"`, `"gpl-3.0"`

#### `update_repo(repo, description, private, default_branch, has_issues, has_wiki, has_discussions, archived)`
Update repo settings. Pass only fields you want to change.

#### `delete_repo(repo, confirm)`
Permanently delete a repo. `confirm` must be `true` — safety guard.

#### `fork_repo(owner_to_fork, repo_to_fork, new_name)`
Fork any public repo into this account.

#### `get_topics(repo)` / `set_topics(repo, topics)`
Read or replace repo topics. Topics must be lowercase with no spaces.

#### `list_branches(repo, limit)` / `get_branch(repo, branch)`
List all branches or get one branch's details and protection status.

#### `create_branch(repo, branch, from_branch)`
Create a branch. `from_branch` defaults to the repo's default branch.

#### `delete_branch(repo, branch)` / `rename_branch(repo, branch, new_name)`

#### `list_commits(repo, branch, path, author, since, until, limit)`
List commits with optional filters. `since`/`until` are ISO 8601 dates.

#### `get_commit(repo, sha)`
Full commit details including files changed, additions, deletions.

#### `list_tags(repo, limit)` / `create_tag(repo, tag, message, sha)`
List tags or create an annotated tag on a specific commit SHA.

---

### Files

#### `list_files(repo, path, branch)`
List files and directories at a path. Empty `path` = repo root.

#### `read_file(repo, path, branch)`
Read a file's content. Returns decoded UTF-8 text, size, and SHA.

#### `create_file(repo, path, content, message, branch)`
Create a new file. Fails if the file already exists.

#### `update_file(repo, path, content, message, branch)`
Update an existing file. Fetches the current SHA automatically.

#### `upsert_file(repo, path, content, message, branch)`
Create or update — use this when you don't know if the file exists yet.
This is the safest default for most write operations.

#### `delete_file(repo, path, message, branch)`
Delete a file. Fetches the current SHA automatically.

#### `get_file_tree(repo, branch, recursive)`
Full file tree of the repo. `recursive=true` includes all subdirectories.
Useful for understanding a repo's structure before editing.

#### `get_raw_file(repo, path, branch)`
Get raw base64-encoded content. Use for binary files.

---

### Pull Requests

#### `list_pulls(repo, state, base, head, sort, direction, limit)`
List PRs. `state`: `"open"` | `"closed"` | `"all"`.

#### `get_pull(repo, pull_number)`
Full PR details: additions, deletions, changed files, reviewers, labels.

#### `create_pull(repo, title, head, base, body, draft, maintainer_can_modify)`
Open a PR. `head` is the source branch, `base` is the target.

#### `update_pull(repo, pull_number, title, body, state, base)`
Update a PR. Pass only what you want to change.

#### `merge_pull(repo, pull_number, commit_title, commit_message, merge_method)`
Merge a PR. `merge_method`: `"merge"` | `"squash"` | `"rebase"`.

#### `list_pull_files(repo, pull_number)`
List files changed in a PR with patch diffs.

#### `get_pull_diff(repo, pull_number)`
Get the raw unified diff of a PR.

#### `list_reviews(repo, pull_number)`
List submitted reviews.

#### `create_review(repo, pull_number, event, body, comments)`
Submit a review. `event`: `"APPROVE"` | `"REQUEST_CHANGES"` | `"COMMENT"`.
`comments` is a list of inline comments: `[{"path": "...", "line": N, "body": "..."}]`

#### `request_reviewers(repo, pull_number, reviewers, team_reviewers)`
Request specific reviewers.

#### `list_pull_comments(repo, pull_number)`
List inline review comments.

#### `add_pull_comment(repo, pull_number, body, commit_id, path, line, side)`
Add an inline comment on a specific line. `side`: `"LEFT"` (old) | `"RIGHT"` (new).

#### `reply_to_review_comment(repo, pull_number, comment_id, body)`
Reply to an existing inline comment thread.

---

### Issues

#### `list_issues(repo, state, labels, assignee, milestone, sort, direction, since, limit)`
List issues. PRs are filtered out automatically.
- `labels`: comma-separated label names
- `since`: ISO 8601 date — only issues updated after this

#### `get_issue(repo, issue_number)`
Full issue details including body, comments count, and milestone.

#### `create_issue(repo, title, body, assignees, labels, milestone)`
Create an issue.

#### `update_issue(repo, issue_number, title, body, state, state_reason, assignees, labels, milestone)`
Update an issue. Pass only fields to change.
- `state_reason`: `"completed"` | `"not_planned"` | `"reopened"`
- `assignees`: pass empty list `[]` to remove all assignees
- `milestone`: pass `0` to remove milestone

#### `close_issue(repo, issue_number, reason)`
Close an issue. `reason`: `"completed"` | `"not_planned"`.

#### `list_issue_comments(repo, issue_number, limit)` / `add_issue_comment(repo, issue_number, body)`
List or add comments. Markdown supported in body.

#### `update_issue_comment(repo, comment_id, body)` / `delete_issue_comment(repo, comment_id)`
Note: `comment_id` is the comment's ID, not the issue number.

#### `list_labels(repo)` / `create_label(repo, name, color, description)`
List labels or create one. `color` is hex without `#` (e.g. `"d73a4a"`).

#### `add_labels_to_issue(repo, issue_number, labels)` / `remove_label_from_issue(repo, issue_number, label)`

#### `list_milestones(repo, state, sort)` / `create_milestone(repo, title, description, due_on)`
`due_on` is ISO 8601 (e.g. `"2025-12-31T00:00:00Z"`).

---

### Actions

#### `list_workflows(repo)` / `get_workflow(repo, workflow_id)`
`workflow_id` can be a numeric ID or filename (e.g. `"ci.yml"`).

#### `trigger_workflow(repo, workflow_id, ref, inputs)`
Trigger a `workflow_dispatch` event. `inputs` is a key-value dict matching
the workflow's defined inputs.

#### `enable_workflow(repo, workflow_id)` / `disable_workflow(repo, workflow_id)`

#### `list_workflow_runs(repo, workflow_id, branch, status, limit)`
Filter by status: `"queued"` | `"in_progress"` | `"completed"` |
`"success"` | `"failure"` | `"cancelled"` | `"skipped"` | `"waiting"`.

#### `get_workflow_run(repo, run_id)`
Full run details including duration, triggering actor, and run attempt.

#### `cancel_workflow_run(repo, run_id)` / `rerun_workflow(repo, run_id, failed_only)`
Cancel an in-progress run, or re-run all jobs or only failed ones.

#### `delete_workflow_run(repo, run_id)`
Remove a run from history.

#### `list_run_jobs(repo, run_id, filter)` / `get_job(repo, job_id)`
`filter`: `"latest"` | `"all"`. `get_job` includes step-level detail.

#### `get_job_logs(repo, job_id)`
Get the raw log output of a job. Use this to diagnose failures.

#### `list_repo_secrets(repo)`
List secret names only. Values are never returned by the GitHub API.

#### `delete_repo_secret(repo, secret_name)`

#### `list_run_artifacts(repo, run_id)` / `delete_artifact(repo, artifact_id)`
Artifacts are files saved by workflow runs (e.g. test reports, binaries).

#### `list_runners(repo)`
List self-hosted runners and their status.

---

### Releases

#### `list_releases(repo, limit)` / `get_release(repo, release_id)`
#### `get_latest_release(repo)` / `get_release_by_tag(repo, tag)`

#### `create_release(repo, tag_name, name, body, draft, prerelease, target_commitish, generate_release_notes)`
- `draft`: create without publishing — useful for staging
- `generate_release_notes`: auto-generate notes from merged PRs since last release
- `target_commitish`: branch or commit SHA to tag (defaults to default branch)

#### `update_release(repo, release_id, tag_name, name, body, draft, prerelease)`
Pass only fields to change.

#### `publish_release(repo, release_id)`
Publish a draft release (sets `draft=false`).

#### `delete_release(repo, release_id)`
Deletes the release but not the associated tag.

#### `list_release_assets(repo, release_id)` / `delete_release_asset(repo, asset_id)`
Assets are files attached to a release (binaries, archives, etc.).

---

### Search

GitHub search has a separate rate limit: 30 requests/minute.

#### `search_code(query, repo, language, path, limit)`
Search for code. Scope to a specific repo with `repo` parameter.

```
query: "def authenticate"
repo: "my-repo"       → searches only test-owner/my-repo
language: "python"
path: "src/"
```

#### `search_my_code(query, language, limit)`
Shorthand — searches code across all repos in this account.

#### `search_repos(query, language, sort, order, limit)`
Find repos on GitHub. `sort`: `"stars"` | `"forks"` | `"updated"`.

#### `search_issues(query, repo, state, label, type, sort, order, limit)`
Search issues and PRs. `type`: `"issue"` | `"pr"`.

#### `search_commits(query, repo, author, since, until, limit)`
Search commit messages.

#### `search_users(query, type, sort, limit)`
Find users or orgs. `type`: `"user"` | `"org"`.

---

## Error handling

Every tool returns either a result dict or an error dict. Error dicts always
have the same shape:

```json
{
  "error": true,
  "status": 404,
  "message": "Not Found",
  "path": "/repos/owner/repo/contents/missing.py"
}
```

The agent can check for `result.get("error")` and handle gracefully.
No tool raises an exception to the agent — errors are returned as data.

Common status codes:

| Status | Meaning |
|---|---|
| 401 | Token invalid or expired |
| 403 | Token lacks required scope |
| 404 | Resource doesn't exist, or private and no access |
| 409 | Conflict (e.g. branch already exists) |
| 422 | Validation failed (e.g. repo name taken, SHA mismatch) |
| 429 | Rate limited — check `get_rate_limit` |

---

## Rate limits

GitHub allows 5000 REST requests/hour and 30 search requests/minute for
authenticated users. The server does not automatically back off — the agent
should call `get_rate_limit` before bulk operations and space out search calls.

Key limits to know:
- Paginated calls count as one request per page (100 items/page)
- Search is a separate limit — don't call it in a tight loop
- GraphQL has its own limit (tracked separately in `get_rate_limit`)

---

## Security

- The token is read from `.env` at startup — never passed to any AI model
- `.env` is gitignored — never committed
- The model only sees tool results, not credentials
- `delete_repo` requires an explicit `confirm=True` parameter
- All destructive operations (`delete_*`) make a single targeted API call —
  no bulk deletes without explicit instruction

---

## Running tests

```bash
# all tests
python -m pytest tests/ -v

# one module
python -m pytest tests/test_actions.py -v

# with coverage
pip install pytest-cov
python -m pytest tests/ --cov=github --cov-report=term-missing
```

Tests use a `MockClient` — no real GitHub calls, no token needed.
164 tests, all passing.

---

## Adding a new module

1. Create `github/my_module.py`:

```python
from .client import GitHubClient, GitHubError

def register(mcp, client: GitHubClient, owner: str):

    @mcp.tool()
    def my_tool(repo: str, thing_id: int) -> dict:
        """
        One-line description shown to the agent.

        repo: repository name
        thing_id: the thing's ID
        """
        try:
            result = client.rest("GET", f"/repos/{owner}/{repo}/things/{thing_id}")
            return {"id": result["id"], "name": result["name"]}
        except GitHubError as e:
            return e.to_dict()
```

2. Register it in `server.py`:

```python
from github import repos, files, pulls, issues, actions, releases, search, my_module
# ...
my_module.register(mcp, client, owner)
```

3. Add tests in `tests/test_my_module.py` following the same pattern.

That's the entire extension surface. No other files need to change.

---

## Planned modules

| Module | What it adds |
|---|---|
| `actions_secrets` | Create/update secrets via libsodium encryption |
| `discussions` | GraphQL-based discussions (create, reply, mark answer) |
| `orgs` | Members, teams, team permissions |
| `projects` | GitHub Projects v2 via GraphQL |
| `gists` | Create and manage gists |
