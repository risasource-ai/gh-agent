"""
github/repos.py

Everything repo-level: create, delete, get info, fork, topics,
branches, tags, default branch changes.

Each function is a plain async def — server.py registers them as MCP tools.
"""

from .client import GitHubClient, GitHubError


def register(mcp, client: GitHubClient, owner: str):
    """Register all repo tools onto the FastMCP server."""

    # ── repos ─────────────────────────────────────────────────────────

    @mcp.tool()
    def list_repos(
        visibility: str = "all",
        sort: str = "updated",
        limit: int = 50,
    ) -> list[dict]:
        """
        List repositories for the authenticated account.

        visibility: "all" | "public" | "private"
        sort: "updated" | "created" | "pushed" | "full_name"
        limit: max number of repos to return (default 50)
        """
        try:
            repos = client.paginate(
                f"/users/{owner}/repos",
                params={"visibility": visibility, "sort": sort},
                limit=limit,
            )
            return [_shape_repo(r) for r in repos]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_repo(repo: str) -> dict:
        """
        Get full details about a specific repository.

        repo: repository name (without owner prefix)
        """
        try:
            r = client.rest("GET", f"/repos/{owner}/{repo}")
            return _shape_repo(r, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def create_repo(
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True,
        gitignore_template: str = "",
        license_template: str = "",
    ) -> dict:
        """
        Create a new repository.

        name: repository name
        description: short description
        private: whether the repo is private (default False)
        auto_init: initialize with a README (default True)
        gitignore_template: e.g. "Python", "Node"
        license_template: e.g. "mit", "apache-2.0"
        """
        try:
            body = {
                "name": name,
                "description": description,
                "private": private,
                "auto_init": auto_init,
            }
            if gitignore_template:
                body["gitignore_template"] = gitignore_template
            if license_template:
                body["license_template"] = license_template

            r = client.rest("POST", "/user/repos", body=body)
            return _shape_repo(r, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def update_repo(
        repo: str,
        description: str | None = None,
        private: bool | None = None,
        default_branch: str | None = None,
        has_issues: bool | None = None,
        has_wiki: bool | None = None,
        has_discussions: bool | None = None,
        archived: bool | None = None,
    ) -> dict:
        """
        Update repository settings.

        repo: repository name
        Pass only the fields you want to change.
        """
        try:
            body = {}
            if description is not None:
                body["description"] = description
            if private is not None:
                body["private"] = private
            if default_branch is not None:
                body["default_branch"] = default_branch
            if has_issues is not None:
                body["has_issues"] = has_issues
            if has_wiki is not None:
                body["has_wiki"] = has_wiki
            if has_discussions is not None:
                body["has_discussions"] = has_discussions
            if archived is not None:
                body["archived"] = archived

            r = client.rest("PATCH", f"/repos/{owner}/{repo}", body=body)
            return _shape_repo(r, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def delete_repo(repo: str, confirm: bool = False) -> dict:
        """
        Permanently delete a repository. This cannot be undone.

        repo: repository name
        confirm: must be True to proceed (safety check)
        """
        if not confirm:
            return {
                "error": True,
                "message": "Set confirm=True to delete. This is irreversible.",
            }
        try:
            client.rest("DELETE", f"/repos/{owner}/{repo}")
            return {"success": True, "deleted": repo}
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def fork_repo(
        owner_to_fork: str,
        repo_to_fork: str,
        new_name: str = "",
    ) -> dict:
        """
        Fork a repository into the authenticated account.

        owner_to_fork: owner of the repo to fork
        repo_to_fork: name of the repo to fork
        new_name: optional new name for the fork
        """
        try:
            body = {}
            if new_name:
                body["name"] = new_name
            r = client.rest(
                "POST",
                f"/repos/{owner_to_fork}/{repo_to_fork}/forks",
                body=body,
            )
            return _shape_repo(r, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def get_topics(repo: str) -> dict:
        """Get the topics (tags) for a repository."""
        try:
            result = client.rest("GET", f"/repos/{owner}/{repo}/topics")
            return {"repo": repo, "topics": result.get("names", [])}
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def set_topics(repo: str, topics: list[str]) -> dict:
        """
        Replace all topics on a repository.

        topics: list of topic strings (lowercase, no spaces)
        """
        try:
            result = client.rest(
                "PUT",
                f"/repos/{owner}/{repo}/topics",
                body={"names": topics},
            )
            return {"repo": repo, "topics": result.get("names", [])}
        except GitHubError as e:
            return e.to_dict()

    # ── branches ─────────────────────────────────────────────────────

    @mcp.tool()
    def list_branches(repo: str, limit: int = 50) -> list[dict]:
        """List all branches in a repository."""
        try:
            branches = client.paginate(
                f"/repos/{owner}/{repo}/branches", limit=limit
            )
            return [
                {
                    "name": b["name"],
                    "sha": b["commit"]["sha"],
                    "protected": b.get("protected", False),
                }
                for b in branches
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_branch(repo: str, branch: str) -> dict:
        """Get details about a specific branch."""
        try:
            b = client.rest("GET", f"/repos/{owner}/{repo}/branches/{branch}")
            return {
                "name": b["name"],
                "sha": b["commit"]["sha"],
                "protected": b.get("protected", False),
                "protection": b.get("protection"),
            }
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def create_branch(repo: str, branch: str, from_branch: str = "") -> dict:
        """
        Create a new branch.

        repo: repository name
        branch: name for the new branch
        from_branch: source branch (defaults to repo's default branch)
        """
        try:
            if not from_branch:
                repo_data = client.rest("GET", f"/repos/{owner}/{repo}")
                from_branch = repo_data["default_branch"]

            source = client.rest(
                "GET", f"/repos/{owner}/{repo}/branches/{from_branch}"
            )
            sha = source["commit"]["sha"]

            client.rest(
                "POST",
                f"/repos/{owner}/{repo}/git/refs",
                body={"ref": f"refs/heads/{branch}", "sha": sha},
            )
            return {"success": True, "branch": branch, "from": from_branch, "sha": sha}
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def delete_branch(repo: str, branch: str) -> dict:
        """Delete a branch from a repository."""
        try:
            client.rest(
                "DELETE",
                f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
            )
            return {"success": True, "deleted": branch}
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def rename_branch(repo: str, branch: str, new_name: str) -> dict:
        """Rename a branch."""
        try:
            result = client.rest(
                "POST",
                f"/repos/{owner}/{repo}/branches/{branch}/rename",
                body={"new_name": new_name},
            )
            return {
                "success": True,
                "old_name": branch,
                "new_name": result.get("name"),
            }
        except GitHubError as e:
            return e.to_dict()

    # ── commits ──────────────────────────────────────────────────────

    @mcp.tool()
    def list_commits(
        repo: str,
        branch: str = "",
        path: str = "",
        author: str = "",
        since: str = "",
        until: str = "",
        limit: int = 30,
    ) -> list[dict]:
        """
        List commits on a branch.

        repo: repository name
        branch: branch name (defaults to default branch)
        path: filter to commits touching this path
        author: filter by author login or email
        since: ISO 8601 date string
        until: ISO 8601 date string
        limit: max commits to return (default 30)
        """
        try:
            params = {}
            if branch:
                params["sha"] = branch
            if path:
                params["path"] = path
            if author:
                params["author"] = author
            if since:
                params["since"] = since
            if until:
                params["until"] = until

            commits = client.paginate(
                f"/repos/{owner}/{repo}/commits", params=params, limit=limit
            )
            return [
                {
                    "sha": c["sha"][:7],
                    "full_sha": c["sha"],
                    "message": c["commit"]["message"].split("\n")[0],
                    "author": c["commit"]["author"]["name"],
                    "date": c["commit"]["author"]["date"],
                    "url": c["html_url"],
                }
                for c in commits
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_commit(repo: str, sha: str) -> dict:
        """Get full details of a specific commit including files changed."""
        try:
            c = client.rest("GET", f"/repos/{owner}/{repo}/commits/{sha}")
            return {
                "sha": c["sha"],
                "message": c["commit"]["message"],
                "author": c["commit"]["author"],
                "stats": c.get("stats"),
                "files": [
                    {
                        "filename": f["filename"],
                        "status": f["status"],
                        "additions": f["additions"],
                        "deletions": f["deletions"],
                    }
                    for f in c.get("files", [])
                ],
                "url": c["html_url"],
            }
        except GitHubError as e:
            return e.to_dict()

    # ── tags ─────────────────────────────────────────────────────────

    @mcp.tool()
    def list_tags(repo: str, limit: int = 30) -> list[dict]:
        """List tags in a repository."""
        try:
            tags = client.paginate(
                f"/repos/{owner}/{repo}/tags", limit=limit
            )
            return [
                {"name": t["name"], "sha": t["commit"]["sha"]}
                for t in tags
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def create_tag(
        repo: str,
        tag: str,
        message: str,
        sha: str,
    ) -> dict:
        """
        Create an annotated tag.

        repo: repository name
        tag: tag name (e.g. "v1.0.0")
        message: tag annotation message
        sha: commit SHA to tag
        """
        try:
            tag_obj = client.rest(
                "POST",
                f"/repos/{owner}/{repo}/git/tags",
                body={
                    "tag": tag,
                    "message": message,
                    "object": sha,
                    "type": "commit",
                },
            )
            client.rest(
                "POST",
                f"/repos/{owner}/{repo}/git/refs",
                body={"ref": f"refs/tags/{tag}", "sha": tag_obj["sha"]},
            )
            return {
                "success": True,
                "tag": tag,
                "sha": tag_obj["sha"],
                "message": message,
            }
        except GitHubError as e:
            return e.to_dict()


# ── shape helpers ─────────────────────────────────────────────────────

def _shape_repo(r: dict, full: bool = False) -> dict:
    base = {
        "name": r["name"],
        "full_name": r["full_name"],
        "description": r.get("description") or "",
        "private": r["private"],
        "url": r["html_url"],
        "default_branch": r.get("default_branch", "main"),
        "updated_at": r.get("updated_at"),
    }
    if full:
        base.update({
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "language": r.get("language"),
            "open_issues": r.get("open_issues_count", 0),
            "has_issues": r.get("has_issues"),
            "has_wiki": r.get("has_wiki"),
            "has_discussions": r.get("has_discussions"),
            "archived": r.get("archived"),
            "clone_url": r.get("clone_url"),
        })
    return base
