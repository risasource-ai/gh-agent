"""
github/issues.py

Issues: create, read, update, close, assign, label.
Labels: create, list, apply.
Milestones: create, list, assign.
Comments: add, edit, delete.
"""

from .client import GitHubClient, GitHubError


def register(mcp, client: GitHubClient, owner: str):

    # ── issues ────────────────────────────────────────────────────────

    @mcp.tool()
    def list_issues(
        repo: str,
        state: str = "open",
        labels: str = "",
        assignee: str = "",
        milestone: str = "",
        sort: str = "created",
        direction: str = "desc",
        since: str = "",
        limit: int = 30,
    ) -> list[dict]:
        """
        List issues in a repository.

        repo: repository name
        state: "open" | "closed" | "all"
        labels: comma-separated label names to filter by
        assignee: filter by assignee login (use "none" for unassigned)
        milestone: milestone number or "*" for any
        sort: "created" | "updated" | "comments"
        direction: "asc" | "desc"
        since: ISO 8601 date — only issues updated after this
        limit: max results
        """
        try:
            params: dict = {"state": state, "sort": sort, "direction": direction}
            if labels:
                params["labels"] = labels
            if assignee:
                params["assignee"] = assignee
            if milestone:
                params["milestone"] = milestone
            if since:
                params["since"] = since

            issues = client.paginate(
                f"/repos/{owner}/{repo}/issues", params=params, limit=limit
            )
            # GitHub returns PRs in the issues list — filter them out
            return [_shape_issue(i) for i in issues if "pull_request" not in i]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_issue(repo: str, issue_number: int) -> dict:
        """
        Get full details of an issue.

        repo: repository name
        issue_number: issue number
        """
        try:
            i = client.rest("GET", f"/repos/{owner}/{repo}/issues/{issue_number}")
            return _shape_issue(i, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def create_issue(
        repo: str,
        title: str,
        body: str = "",
        assignees: list[str] | None = None,
        labels: list[str] | None = None,
        milestone: int | None = None,
    ) -> dict:
        """
        Create a new issue.

        repo: repository name
        title: issue title
        body: issue description (markdown supported)
        assignees: list of GitHub usernames to assign
        labels: list of label names to apply
        milestone: milestone number to assign
        """
        try:
            payload: dict = {"title": title, "body": body}
            if assignees:
                payload["assignees"] = assignees
            if labels:
                payload["labels"] = labels
            if milestone is not None:
                payload["milestone"] = milestone

            i = client.rest(
                "POST", f"/repos/{owner}/{repo}/issues", body=payload
            )
            return _shape_issue(i, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def update_issue(
        repo: str,
        issue_number: int,
        title: str = "",
        body: str = "",
        state: str = "",
        state_reason: str = "",
        assignees: list[str] | None = None,
        labels: list[str] | None = None,
        milestone: int | None = None,
    ) -> dict:
        """
        Update an issue.

        repo: repository name
        issue_number: issue number
        title: new title
        body: new description
        state: "open" or "closed"
        state_reason: "completed" | "not_planned" | "reopened"
        assignees: replace assignees (pass empty list to remove all)
        labels: replace labels (pass empty list to remove all)
        milestone: assign milestone by number (pass 0 to remove)
        """
        try:
            payload: dict = {}
            if title:
                payload["title"] = title
            if body:
                payload["body"] = body
            if state:
                payload["state"] = state
            if state_reason:
                payload["state_reason"] = state_reason
            if assignees is not None:
                payload["assignees"] = assignees
            if labels is not None:
                payload["labels"] = labels
            if milestone is not None:
                payload["milestone"] = milestone if milestone > 0 else None

            i = client.rest(
                "PATCH",
                f"/repos/{owner}/{repo}/issues/{issue_number}",
                body=payload,
            )
            return _shape_issue(i, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def close_issue(
        repo: str,
        issue_number: int,
        reason: str = "completed",
    ) -> dict:
        """
        Close an issue.

        repo: repository name
        issue_number: issue number
        reason: "completed" | "not_planned"
        """
        try:
            i = client.rest(
                "PATCH",
                f"/repos/{owner}/{repo}/issues/{issue_number}",
                body={"state": "closed", "state_reason": reason},
            )
            return _shape_issue(i)
        except GitHubError as e:
            return e.to_dict()

    # ── issue comments ────────────────────────────────────────────────

    @mcp.tool()
    def list_issue_comments(
        repo: str,
        issue_number: int,
        limit: int = 50,
    ) -> list[dict]:
        """
        List comments on an issue.

        repo: repository name
        issue_number: issue number
        """
        try:
            comments = client.paginate(
                f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                limit=limit,
            )
            return [_shape_comment(c) for c in comments]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def add_issue_comment(repo: str, issue_number: int, body: str) -> dict:
        """
        Add a comment to an issue or pull request.

        repo: repository name
        issue_number: issue or PR number
        body: comment text (markdown supported)
        """
        try:
            c = client.rest(
                "POST",
                f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                body={"body": body},
            )
            return _shape_comment(c)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def update_issue_comment(
        repo: str, comment_id: int, body: str
    ) -> dict:
        """
        Edit an existing issue comment.

        repo: repository name
        comment_id: the comment ID (not the issue number)
        body: new comment text
        """
        try:
            c = client.rest(
                "PATCH",
                f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
                body={"body": body},
            )
            return _shape_comment(c)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def delete_issue_comment(repo: str, comment_id: int) -> dict:
        """
        Delete an issue comment.

        repo: repository name
        comment_id: the comment ID
        """
        try:
            client.rest(
                "DELETE",
                f"/repos/{owner}/{repo}/issues/comments/{comment_id}",
            )
            return {"success": True, "deleted_comment": comment_id}
        except GitHubError as e:
            return e.to_dict()

    # ── labels ────────────────────────────────────────────────────────

    @mcp.tool()
    def list_labels(repo: str) -> list[dict]:
        """List all labels in a repository."""
        try:
            labels = client.paginate(f"/repos/{owner}/{repo}/labels")
            return [_shape_label(l) for l in labels]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def create_label(
        repo: str, name: str, color: str, description: str = ""
    ) -> dict:
        """
        Create a new label.

        repo: repository name
        name: label name
        color: hex color without # (e.g. "f29513")
        description: short description
        """
        try:
            l = client.rest(
                "POST",
                f"/repos/{owner}/{repo}/labels",
                body={"name": name, "color": color, "description": description},
            )
            return _shape_label(l)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def add_labels_to_issue(
        repo: str, issue_number: int, labels: list[str]
    ) -> list[dict]:
        """
        Add labels to an issue or PR.

        repo: repository name
        issue_number: issue or PR number
        labels: list of label names to add
        """
        try:
            result = client.rest(
                "POST",
                f"/repos/{owner}/{repo}/issues/{issue_number}/labels",
                body={"labels": labels},
            )
            return [_shape_label(l) for l in result]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def remove_label_from_issue(
        repo: str, issue_number: int, label: str
    ) -> dict:
        """
        Remove a specific label from an issue or PR.

        repo: repository name
        issue_number: issue or PR number
        label: label name to remove
        """
        try:
            client.rest(
                "DELETE",
                f"/repos/{owner}/{repo}/issues/{issue_number}/labels/{label}",
            )
            return {"success": True, "removed": label}
        except GitHubError as e:
            return e.to_dict()

    # ── milestones ────────────────────────────────────────────────────

    @mcp.tool()
    def list_milestones(
        repo: str, state: str = "open", sort: str = "due_on"
    ) -> list[dict]:
        """
        List milestones in a repository.

        repo: repository name
        state: "open" | "closed" | "all"
        sort: "due_on" | "completeness"
        """
        try:
            milestones = client.paginate(
                f"/repos/{owner}/{repo}/milestones",
                params={"state": state, "sort": sort},
            )
            return [_shape_milestone(m) for m in milestones]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def create_milestone(
        repo: str,
        title: str,
        description: str = "",
        due_on: str = "",
    ) -> dict:
        """
        Create a milestone.

        repo: repository name
        title: milestone title
        description: milestone description
        due_on: ISO 8601 due date (e.g. "2025-12-31T00:00:00Z")
        """
        try:
            body: dict = {"title": title, "description": description}
            if due_on:
                body["due_on"] = due_on
            m = client.rest(
                "POST", f"/repos/{owner}/{repo}/milestones", body=body
            )
            return _shape_milestone(m)
        except GitHubError as e:
            return e.to_dict()


# ── shape helpers ─────────────────────────────────────────────────────

def _shape_issue(i: dict, full: bool = False) -> dict:
    base = {
        "number": i["number"],
        "title": i["title"],
        "state": i["state"],
        "user": i["user"]["login"],
        "labels": [l["name"] for l in i.get("labels", [])],
        "assignees": [a["login"] for a in i.get("assignees", [])],
        "created_at": i.get("created_at"),
        "updated_at": i.get("updated_at"),
        "url": i["html_url"],
    }
    if full:
        base.update({
            "body": i.get("body", ""),
            "closed_at": i.get("closed_at"),
            "comments": i.get("comments", 0),
            "milestone": _shape_milestone(i["milestone"]) if i.get("milestone") else None,
        })
    return base


def _shape_comment(c: dict) -> dict:
    return {
        "id": c["id"],
        "user": c["user"]["login"],
        "body": c["body"],
        "created_at": c.get("created_at"),
        "updated_at": c.get("updated_at"),
        "url": c.get("html_url"),
    }


def _shape_label(l: dict) -> dict:
    return {
        "name": l["name"],
        "color": l["color"],
        "description": l.get("description", ""),
    }


def _shape_milestone(m: dict) -> dict:
    return {
        "number": m["number"],
        "title": m["title"],
        "state": m["state"],
        "open_issues": m.get("open_issues", 0),
        "closed_issues": m.get("closed_issues", 0),
        "due_on": m.get("due_on"),
    }
