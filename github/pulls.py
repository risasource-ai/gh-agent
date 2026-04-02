"""
github/pulls.py

Pull requests: create, list, get, update, merge.
Reviews: request, submit, list.
Comments: inline review comments, general PR comments.
"""

from .client import GitHubClient, GitHubError


def register(mcp, client: GitHubClient, owner: str):

    # ── pull requests ─────────────────────────────────────────────────

    @mcp.tool()
    def list_pulls(
        repo: str,
        state: str = "open",
        base: str = "",
        head: str = "",
        sort: str = "created",
        direction: str = "desc",
        limit: int = 30,
    ) -> list[dict]:
        """
        List pull requests in a repository.

        repo: repository name
        state: "open" | "closed" | "all"
        base: filter by base branch name
        head: filter by head branch (format: "owner:branch")
        sort: "created" | "updated" | "popularity" | "long-running"
        direction: "asc" | "desc"
        limit: max results
        """
        try:
            params: dict = {"state": state, "sort": sort, "direction": direction}
            if base:
                params["base"] = base
            if head:
                params["head"] = head
            pulls = client.paginate(
                f"/repos/{owner}/{repo}/pulls", params=params, limit=limit
            )
            return [_shape_pull(p) for p in pulls]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_pull(repo: str, pull_number: int) -> dict:
        """
        Get full details of a pull request including diff stats.

        repo: repository name
        pull_number: PR number
        """
        try:
            p = client.rest("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}")
            return _shape_pull(p, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def create_pull(
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
        draft: bool = False,
        maintainer_can_modify: bool = True,
    ) -> dict:
        """
        Create a pull request.

        repo: repository name
        title: PR title
        head: branch with your changes (e.g. "feature/my-feature")
        base: branch to merge into (e.g. "main")
        body: PR description (markdown supported)
        draft: open as draft PR
        maintainer_can_modify: allow maintainers to push to head branch
        """
        try:
            p = client.rest(
                "POST",
                f"/repos/{owner}/{repo}/pulls",
                body={
                    "title": title,
                    "head": head,
                    "base": base,
                    "body": body,
                    "draft": draft,
                    "maintainer_can_modify": maintainer_can_modify,
                },
            )
            return _shape_pull(p, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def update_pull(
        repo: str,
        pull_number: int,
        title: str = "",
        body: str = "",
        state: str = "",
        base: str = "",
    ) -> dict:
        """
        Update a pull request.

        repo: repository name
        pull_number: PR number
        title: new title
        body: new description
        state: "open" or "closed"
        base: change the target base branch
        """
        try:
            payload: dict = {}
            if title:
                payload["title"] = title
            if body:
                payload["body"] = body
            if state:
                payload["state"] = state
            if base:
                payload["base"] = base

            p = client.rest(
                "PATCH",
                f"/repos/{owner}/{repo}/pulls/{pull_number}",
                body=payload,
            )
            return _shape_pull(p, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def merge_pull(
        repo: str,
        pull_number: int,
        commit_title: str = "",
        commit_message: str = "",
        merge_method: str = "merge",
    ) -> dict:
        """
        Merge a pull request.

        repo: repository name
        pull_number: PR number
        commit_title: title for the merge commit (optional)
        commit_message: message for the merge commit (optional)
        merge_method: "merge" | "squash" | "rebase"
        """
        try:
            body: dict = {"merge_method": merge_method}
            if commit_title:
                body["commit_title"] = commit_title
            if commit_message:
                body["commit_message"] = commit_message

            result = client.rest(
                "PUT",
                f"/repos/{owner}/{repo}/pulls/{pull_number}/merge",
                body=body,
            )
            return {
                "success": True,
                "merged": True,
                "sha": result.get("sha"),
                "message": result.get("message"),
            }
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def list_pull_files(repo: str, pull_number: int) -> list[dict]:
        """
        List files changed in a pull request.

        repo: repository name
        pull_number: PR number
        """
        try:
            files = client.paginate(
                f"/repos/{owner}/{repo}/pulls/{pull_number}/files"
            )
            return [
                {
                    "filename": f["filename"],
                    "status": f["status"],
                    "additions": f["additions"],
                    "deletions": f["deletions"],
                    "changes": f["changes"],
                    "patch": f.get("patch", ""),
                }
                for f in files
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_pull_diff(repo: str, pull_number: int) -> dict:
        """
        Get the raw diff of a pull request.

        repo: repository name
        pull_number: PR number
        """
        try:
            diff = client.rest_raw(
                "GET",
                f"/repos/{owner}/{repo}/pulls/{pull_number}",
                accept="application/vnd.github.diff",
            )
            return {"diff": diff, "pull_number": pull_number}
        except GitHubError as e:
            return e.to_dict()

    # ── reviews ───────────────────────────────────────────────────────

    @mcp.tool()
    def list_reviews(repo: str, pull_number: int) -> list[dict]:
        """
        List reviews on a pull request.

        repo: repository name
        pull_number: PR number
        """
        try:
            reviews = client.paginate(
                f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
            )
            return [
                {
                    "id": r["id"],
                    "user": r["user"]["login"],
                    "state": r["state"],
                    "body": r.get("body", ""),
                    "submitted_at": r.get("submitted_at"),
                    "commit_id": r.get("commit_id"),
                }
                for r in reviews
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def create_review(
        repo: str,
        pull_number: int,
        event: str,
        body: str = "",
        comments: list[dict] | None = None,
    ) -> dict:
        """
        Submit a review on a pull request.

        repo: repository name
        pull_number: PR number
        event: "APPROVE" | "REQUEST_CHANGES" | "COMMENT"
        body: overall review comment
        comments: list of inline comments, each with:
                  {"path": str, "line": int, "body": str}
        """
        try:
            payload: dict = {"event": event}
            if body:
                payload["body"] = body
            if comments:
                payload["comments"] = comments

            r = client.rest(
                "POST",
                f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews",
                body=payload,
            )
            return {
                "success": True,
                "review_id": r["id"],
                "state": r["state"],
                "user": r["user"]["login"],
            }
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def request_reviewers(
        repo: str,
        pull_number: int,
        reviewers: list[str] | None = None,
        team_reviewers: list[str] | None = None,
    ) -> dict:
        """
        Request reviewers for a pull request.

        repo: repository name
        pull_number: PR number
        reviewers: list of GitHub usernames
        team_reviewers: list of team slugs
        """
        try:
            body: dict = {}
            if reviewers:
                body["reviewers"] = reviewers
            if team_reviewers:
                body["team_reviewers"] = team_reviewers

            client.rest(
                "POST",
                f"/repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers",
                body=body,
            )
            return {"success": True, "pull_number": pull_number}
        except GitHubError as e:
            return e.to_dict()

    # ── comments ─────────────────────────────────────────────────────

    @mcp.tool()
    def list_pull_comments(repo: str, pull_number: int) -> list[dict]:
        """
        List review comments (inline) on a pull request.

        repo: repository name
        pull_number: PR number
        """
        try:
            comments = client.paginate(
                f"/repos/{owner}/{repo}/pulls/{pull_number}/comments"
            )
            return [_shape_review_comment(c) for c in comments]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def add_pull_comment(
        repo: str,
        pull_number: int,
        body: str,
        commit_id: str,
        path: str,
        line: int,
        side: str = "RIGHT",
    ) -> dict:
        """
        Add an inline review comment on a specific line.

        repo: repository name
        pull_number: PR number
        body: comment text
        commit_id: commit SHA the comment is on
        path: file path
        line: line number in the file
        side: "LEFT" (old) | "RIGHT" (new)
        """
        try:
            c = client.rest(
                "POST",
                f"/repos/{owner}/{repo}/pulls/{pull_number}/comments",
                body={
                    "body": body,
                    "commit_id": commit_id,
                    "path": path,
                    "line": line,
                    "side": side,
                },
            )
            return _shape_review_comment(c)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def reply_to_review_comment(
        repo: str,
        pull_number: int,
        comment_id: int,
        body: str,
    ) -> dict:
        """
        Reply to an existing review comment thread.

        repo: repository name
        pull_number: PR number
        comment_id: ID of the comment to reply to
        body: reply text
        """
        try:
            c = client.rest(
                "POST",
                f"/repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies",
                body={"body": body},
            )
            return _shape_review_comment(c)
        except GitHubError as e:
            return e.to_dict()


# ── shape helpers ─────────────────────────────────────────────────────

def _shape_pull(p: dict, full: bool = False) -> dict:
    base = {
        "number": p["number"],
        "title": p["title"],
        "state": p["state"],
        "draft": p.get("draft", False),
        "user": p["user"]["login"],
        "head": p["head"]["ref"],
        "base": p["base"]["ref"],
        "created_at": p.get("created_at"),
        "updated_at": p.get("updated_at"),
        "url": p["html_url"],
    }
    if full:
        base.update({
            "body": p.get("body", ""),
            "merged": p.get("merged", False),
            "mergeable": p.get("mergeable"),
            "merged_at": p.get("merged_at"),
            "merged_by": p["merged_by"]["login"] if p.get("merged_by") else None,
            "commits": p.get("commits"),
            "additions": p.get("additions"),
            "deletions": p.get("deletions"),
            "changed_files": p.get("changed_files"),
            "reviewers": [r["login"] for r in p.get("requested_reviewers", [])],
            "labels": [l["name"] for l in p.get("labels", [])],
        })
    return base


def _shape_review_comment(c: dict) -> dict:
    return {
        "id": c["id"],
        "user": c["user"]["login"],
        "body": c["body"],
        "path": c.get("path"),
        "line": c.get("line"),
        "side": c.get("side"),
        "created_at": c.get("created_at"),
        "url": c.get("html_url"),
    }
