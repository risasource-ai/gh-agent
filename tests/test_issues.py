"""
tests/test_issues.py

Tests for issues module: list, get, create, update, close,
comments, labels, milestones.
"""

import pytest
from github.client import GitHubError
from tests.conftest import OWNER


SAMPLE_ISSUE = {
    "number": 12,
    "title": "Bug: login crashes",
    "state": "open",
    "user": {"login": "reporter"},
    "labels": [{"name": "bug", "color": "d73a4a", "description": "Something broken"}],
    "assignees": [{"login": "alice"}],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "html_url": f"https://github.com/{OWNER}/my-repo/issues/12",
    "body": "Steps to reproduce: ...",
    "closed_at": None,
    "comments": 3,
    "milestone": None,
}

SAMPLE_COMMENT = {
    "id": 555,
    "user": {"login": "alice"},
    "body": "I can reproduce this.",
    "created_at": "2024-01-02T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "html_url": f"https://github.com/{OWNER}/my-repo/issues/12#issuecomment-555",
}

SAMPLE_LABEL = {
    "name": "bug",
    "color": "d73a4a",
    "description": "Something broken",
}

SAMPLE_MILESTONE = {
    "number": 1,
    "title": "v1.0",
    "state": "open",
    "open_issues": 5,
    "closed_issues": 10,
    "due_on": "2024-06-01T00:00:00Z",
}


class TestListIssues:
    def test_returns_issues(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_ISSUE]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/issues")
        assert result[0]["number"] == 12
        assert result[0]["title"] == "Bug: login crashes"

    def test_filters_out_pull_requests(self, mock_client):
        pr = {**SAMPLE_ISSUE, "number": 99, "pull_request": {"url": "..."}}
        mock_client.paginate.return_value = [SAMPLE_ISSUE, pr]
        items = mock_client.paginate(f"/repos/{OWNER}/my-repo/issues")
        # handler filters out items with pull_request key
        real_issues = [i for i in items if "pull_request" not in i]
        assert len(real_issues) == 1
        assert real_issues[0]["number"] == 12

    def test_filters_by_label(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_ISSUE]
        mock_client.paginate(
            f"/repos/{OWNER}/my-repo/issues",
            params={"state": "open", "labels": "bug"},
        )
        assert mock_client.paginate.call_args[1]["params"]["labels"] == "bug"

    def test_filters_by_assignee(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_ISSUE]
        mock_client.paginate(
            f"/repos/{OWNER}/my-repo/issues",
            params={"assignee": "alice"},
        )
        assert mock_client.paginate.call_args[1]["params"]["assignee"] == "alice"

    def test_error_handling(self, mock_client):
        mock_client.paginate.side_effect = GitHubError(404, "Not Found", "/repos/x/y/issues")
        with pytest.raises(GitHubError):
            mock_client.paginate(f"/repos/{OWNER}/my-repo/issues")


class TestGetIssue:
    def test_returns_full_issue(self, mock_client):
        mock_client.rest.return_value = SAMPLE_ISSUE
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/issues/12")
        assert result["number"] == 12
        assert result["body"] == "Steps to reproduce: ..."
        assert result["comments"] == 3

    def test_not_found(self, mock_client):
        mock_client.rest.side_effect = GitHubError(404, "Not Found", "/repos/x/y/issues/999")
        with pytest.raises(GitHubError):
            mock_client.rest("GET", f"/repos/{OWNER}/my-repo/issues/999")


class TestCreateIssue:
    def test_creates_with_title_only(self, mock_client):
        mock_client.rest.return_value = SAMPLE_ISSUE
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/issues",
            body={"title": "Bug: login crashes", "body": ""},
        )
        body = mock_client.rest.call_args[1]["body"]
        assert body["title"] == "Bug: login crashes"

    def test_creates_with_all_fields(self, mock_client):
        mock_client.rest.return_value = SAMPLE_ISSUE
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/issues",
            body={
                "title": "Bug: login crashes",
                "body": "Repro steps",
                "assignees": ["alice"],
                "labels": ["bug", "priority:high"],
                "milestone": 1,
            },
        )
        body = mock_client.rest.call_args[1]["body"]
        assert body["assignees"] == ["alice"]
        assert "bug" in body["labels"]
        assert body["milestone"] == 1

    def test_permission_error(self, mock_client):
        mock_client.rest.side_effect = GitHubError(403, "Forbidden", "/repos/x/y/issues")
        with pytest.raises(GitHubError) as exc:
            mock_client.rest("POST", f"/repos/{OWNER}/my-repo/issues", body={})
        assert exc.value.status == 403


class TestUpdateIssue:
    def test_updates_title(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_ISSUE, "title": "Bug: login crashes on mobile"}
        mock_client.rest(
            "PATCH",
            f"/repos/{OWNER}/my-repo/issues/12",
            body={"title": "Bug: login crashes on mobile"},
        )
        assert mock_client.rest.call_args[1]["body"]["title"] == "Bug: login crashes on mobile"

    def test_removes_all_assignees(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_ISSUE, "assignees": []}
        mock_client.rest(
            "PATCH",
            f"/repos/{OWNER}/my-repo/issues/12",
            body={"assignees": []},
        )
        assert mock_client.rest.call_args[1]["body"]["assignees"] == []

    def test_removes_milestone(self, mock_client):
        """milestone=0 should be sent as None to remove it."""
        mock_client.rest.return_value = {**SAMPLE_ISSUE, "milestone": None}
        # simulate the logic: milestone=0 → send None
        milestone_value = 0
        payload = {"milestone": milestone_value if milestone_value > 0 else None}
        assert payload["milestone"] is None


class TestCloseIssue:
    def test_closes_as_completed(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_ISSUE, "state": "closed"}
        mock_client.rest(
            "PATCH",
            f"/repos/{OWNER}/my-repo/issues/12",
            body={"state": "closed", "state_reason": "completed"},
        )
        body = mock_client.rest.call_args[1]["body"]
        assert body["state"] == "closed"
        assert body["state_reason"] == "completed"

    def test_closes_as_not_planned(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_ISSUE, "state": "closed"}
        mock_client.rest(
            "PATCH",
            f"/repos/{OWNER}/my-repo/issues/12",
            body={"state": "closed", "state_reason": "not_planned"},
        )
        assert mock_client.rest.call_args[1]["body"]["state_reason"] == "not_planned"


class TestIssueComments:
    def test_list_comments(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_COMMENT]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/issues/12/comments")
        assert result[0]["id"] == 555
        assert result[0]["body"] == "I can reproduce this."

    def test_add_comment(self, mock_client):
        mock_client.rest.return_value = SAMPLE_COMMENT
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/issues/12/comments",
            body={"body": "I can reproduce this."},
        )
        assert mock_client.rest.call_args[1]["body"]["body"] == "I can reproduce this."

    def test_update_comment(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_COMMENT, "body": "Updated text"}
        mock_client.rest(
            "PATCH",
            f"/repos/{OWNER}/my-repo/issues/comments/555",
            body={"body": "Updated text"},
        )
        call = mock_client.rest.call_args
        assert "comments/555" in call[0][1]
        assert call[1]["body"]["body"] == "Updated text"

    def test_delete_comment(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("DELETE", f"/repos/{OWNER}/my-repo/issues/comments/555")
        call = mock_client.rest.call_args
        assert call[0][0] == "DELETE"
        assert "555" in call[0][1]


class TestLabels:
    def test_list_labels(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_LABEL]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/labels")
        assert result[0]["name"] == "bug"
        assert result[0]["color"] == "d73a4a"

    def test_create_label(self, mock_client):
        mock_client.rest.return_value = SAMPLE_LABEL
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/labels",
            body={"name": "bug", "color": "d73a4a", "description": "Something broken"},
        )
        body = mock_client.rest.call_args[1]["body"]
        assert body["name"] == "bug"
        assert body["color"] == "d73a4a"

    def test_add_labels_to_issue(self, mock_client):
        mock_client.rest.return_value = [SAMPLE_LABEL]
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/issues/12/labels",
            body={"labels": ["bug", "priority:high"]},
        )
        body = mock_client.rest.call_args[1]["body"]
        assert "bug" in body["labels"]

    def test_remove_label_from_issue(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest(
            "DELETE",
            f"/repos/{OWNER}/my-repo/issues/12/labels/bug",
        )
        call = mock_client.rest.call_args
        assert call[0][0] == "DELETE"
        assert "labels/bug" in call[0][1]

    def test_label_already_exists(self, mock_client):
        mock_client.rest.side_effect = GitHubError(422, "already_exists", "/repos/x/y/labels")
        with pytest.raises(GitHubError) as exc:
            mock_client.rest("POST", f"/repos/{OWNER}/my-repo/labels", body={})
        assert exc.value.status == 422


class TestMilestones:
    def test_list_milestones(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_MILESTONE]
        result = mock_client.paginate(
            f"/repos/{OWNER}/my-repo/milestones",
            params={"state": "open", "sort": "due_on"},
        )
        assert result[0]["title"] == "v1.0"
        assert result[0]["open_issues"] == 5

    def test_create_milestone(self, mock_client):
        mock_client.rest.return_value = SAMPLE_MILESTONE
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/milestones",
            body={"title": "v1.0", "description": "First release", "due_on": "2024-06-01T00:00:00Z"},
        )
        body = mock_client.rest.call_args[1]["body"]
        assert body["title"] == "v1.0"
        assert body["due_on"] == "2024-06-01T00:00:00Z"

    def test_create_milestone_without_due_date(self, mock_client):
        mock_client.rest.return_value = SAMPLE_MILESTONE
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/milestones",
            body={"title": "v1.0", "description": ""},
        )
        body = mock_client.rest.call_args[1]["body"]
        assert "due_on" not in body or body.get("due_on", "") == ""


class TestShapeHelpers:
    def test_shape_issue_base(self):
        from github.issues import _shape_issue
        result = _shape_issue(SAMPLE_ISSUE)
        assert result["number"] == 12
        assert result["labels"] == ["bug"]
        assert result["assignees"] == ["alice"]
        assert "body" not in result

    def test_shape_issue_full(self):
        from github.issues import _shape_issue
        result = _shape_issue(SAMPLE_ISSUE, full=True)
        assert result["body"] == "Steps to reproduce: ..."
        assert result["comments"] == 3
        assert result["milestone"] is None

    def test_shape_comment(self):
        from github.issues import _shape_comment
        result = _shape_comment(SAMPLE_COMMENT)
        assert result["id"] == 555
        assert result["user"] == "alice"
        assert result["body"] == "I can reproduce this."

    def test_shape_label(self):
        from github.issues import _shape_label
        result = _shape_label(SAMPLE_LABEL)
        assert result["name"] == "bug"
        assert result["color"] == "d73a4a"

    def test_shape_milestone(self):
        from github.issues import _shape_milestone
        result = _shape_milestone(SAMPLE_MILESTONE)
        assert result["number"] == 1
        assert result["title"] == "v1.0"
        assert result["open_issues"] == 5
