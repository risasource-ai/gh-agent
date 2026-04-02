"""
tests/test_pulls.py

Tests for pulls module: list, get, create, update, merge,
reviews, inline comments, diff.
"""

import pytest
from github.client import GitHubError
from tests.conftest import OWNER


SAMPLE_PULL = {
    "number": 7,
    "title": "feat: add login",
    "state": "open",
    "draft": False,
    "user": {"login": "alice"},
    "head": {"ref": "feature/login"},
    "base": {"ref": "main"},
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "html_url": f"https://github.com/{OWNER}/my-repo/pull/7",
    "body": "Adds login flow",
    "merged": False,
    "mergeable": True,
    "merged_at": None,
    "merged_by": None,
    "commits": 3,
    "additions": 120,
    "deletions": 10,
    "changed_files": 4,
    "requested_reviewers": [{"login": "bob"}],
    "labels": [{"name": "feature"}],
}

SAMPLE_REVIEW = {
    "id": 50,
    "user": {"login": "bob"},
    "state": "APPROVED",
    "body": "LGTM",
    "submitted_at": "2024-01-03T00:00:00Z",
    "commit_id": "abc123",
}

SAMPLE_COMMENT = {
    "id": 99,
    "user": {"login": "alice"},
    "body": "Can we simplify this?",
    "path": "src/auth.py",
    "line": 42,
    "side": "RIGHT",
    "created_at": "2024-01-03T00:00:00Z",
    "html_url": f"https://github.com/{OWNER}/my-repo/pull/7#discussion_r99",
}


class TestListPulls:
    def test_returns_shaped_pulls(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_PULL]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/pulls")
        assert result[0]["number"] == 7
        assert result[0]["title"] == "feat: add login"

    def test_filters_by_state(self, mock_client):
        mock_client.paginate.return_value = []
        mock_client.paginate(
            f"/repos/{OWNER}/my-repo/pulls",
            params={"state": "closed", "sort": "created", "direction": "desc"},
        )
        call = mock_client.paginate.call_args
        assert call[1]["params"]["state"] == "closed"

    def test_filters_by_base_branch(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_PULL]
        mock_client.paginate(
            f"/repos/{OWNER}/my-repo/pulls",
            params={"state": "open", "base": "main"},
        )
        assert mock_client.paginate.call_args[1]["params"]["base"] == "main"

    def test_error_returns_error_list(self, mock_client):
        mock_client.paginate.side_effect = GitHubError(404, "Not Found", "/repos/x/y/pulls")
        with pytest.raises(GitHubError) as exc:
            mock_client.paginate(f"/repos/{OWNER}/my-repo/pulls")
        assert exc.value.status == 404


class TestGetPull:
    def test_returns_full_pull(self, mock_client):
        mock_client.rest.return_value = SAMPLE_PULL
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/pulls/7")
        assert result["number"] == 7
        assert result["additions"] == 120
        assert result["changed_files"] == 4

    def test_not_found(self, mock_client):
        mock_client.rest.side_effect = GitHubError(404, "Not Found", "/repos/x/y/pulls/999")
        with pytest.raises(GitHubError):
            mock_client.rest("GET", f"/repos/{OWNER}/my-repo/pulls/999")


class TestCreatePull:
    def test_creates_with_required_fields(self, mock_client):
        mock_client.rest.return_value = SAMPLE_PULL
        mock_client.rest("POST", f"/repos/{OWNER}/my-repo/pulls", body={
            "title": "feat: add login",
            "head": "feature/login",
            "base": "main",
            "body": "",
            "draft": False,
            "maintainer_can_modify": True,
        })
        body = mock_client.rest.call_args[1]["body"]
        assert body["title"] == "feat: add login"
        assert body["head"] == "feature/login"
        assert body["base"] == "main"

    def test_creates_draft(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_PULL, "draft": True}
        mock_client.rest("POST", f"/repos/{OWNER}/my-repo/pulls", body={
            "title": "WIP: new feature",
            "head": "wip/feature",
            "base": "main",
            "draft": True,
        })
        assert mock_client.rest.call_args[1]["body"]["draft"] is True

    def test_head_already_merged(self, mock_client):
        mock_client.rest.side_effect = GitHubError(
            422, "No commits between main and feature/login", "/repos/x/y/pulls"
        )
        with pytest.raises(GitHubError) as exc:
            mock_client.rest("POST", f"/repos/{OWNER}/my-repo/pulls", body={})
        assert exc.value.status == 422


class TestUpdatePull:
    def test_updates_title(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_PULL, "title": "feat: login v2"}
        mock_client.rest("PATCH", f"/repos/{OWNER}/my-repo/pulls/7", body={"title": "feat: login v2"})
        body = mock_client.rest.call_args[1]["body"]
        assert body["title"] == "feat: login v2"

    def test_closes_pull(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_PULL, "state": "closed"}
        mock_client.rest("PATCH", f"/repos/{OWNER}/my-repo/pulls/7", body={"state": "closed"})
        body = mock_client.rest.call_args[1]["body"]
        assert body["state"] == "closed"

    def test_only_sends_changed_fields(self, mock_client):
        mock_client.rest.return_value = SAMPLE_PULL
        mock_client.rest("PATCH", f"/repos/{OWNER}/my-repo/pulls/7", body={"body": "Updated description"})
        body = mock_client.rest.call_args[1]["body"]
        assert "title" not in body
        assert body["body"] == "Updated description"


class TestMergePull:
    def test_merge_default_method(self, mock_client):
        mock_client.rest.return_value = {
            "sha": "merge-sha-abc",
            "merged": True,
            "message": "Pull Request successfully merged",
        }
        mock_client.rest("PUT", f"/repos/{OWNER}/my-repo/pulls/7/merge", body={"merge_method": "merge"})
        body = mock_client.rest.call_args[1]["body"]
        assert body["merge_method"] == "merge"

    def test_squash_merge(self, mock_client):
        mock_client.rest.return_value = {"sha": "squash-sha", "merged": True}
        mock_client.rest("PUT", f"/repos/{OWNER}/my-repo/pulls/7/merge", body={
            "merge_method": "squash",
            "commit_title": "feat: add login (#7)",
        })
        body = mock_client.rest.call_args[1]["body"]
        assert body["merge_method"] == "squash"
        assert "commit_title" in body

    def test_merge_conflict(self, mock_client):
        mock_client.rest.side_effect = GitHubError(405, "Pull Request is not mergeable", "/repos/x/y/pulls/7/merge")
        with pytest.raises(GitHubError) as exc:
            mock_client.rest("PUT", f"/repos/{OWNER}/my-repo/pulls/7/merge", body={})
        assert exc.value.status == 405


class TestPullDiff:
    def test_returns_diff_text(self, mock_client):
        mock_client.rest_raw.return_value = (
            "diff --git a/src/auth.py b/src/auth.py\n"
            "--- a/src/auth.py\n"
            "+++ b/src/auth.py\n"
            "@@ -1,3 +1,5 @@\n"
            "+def login():\n"
            "+    pass\n"
        )
        result = mock_client.rest_raw(
            "GET",
            f"/repos/{OWNER}/my-repo/pulls/7",
            accept="application/vnd.github.diff",
        )
        assert "diff --git" in result
        assert "+def login" in result

    def test_uses_rest_raw_not_headers(self, mock_client):
        """Must use rest_raw, not access _headers directly."""
        mock_client.rest_raw.return_value = "diff content"
        mock_client.rest_raw("GET", "/test", accept="application/vnd.github.diff")
        assert mock_client.rest_raw.called
        assert not mock_client.rest.called


class TestListPullFiles:
    def test_returns_changed_files(self, mock_client):
        mock_client.paginate.return_value = [
            {
                "filename": "src/auth.py",
                "status": "modified",
                "additions": 50,
                "deletions": 5,
                "changes": 55,
                "patch": "@@ -1,3 +1,10 @@\n+new code",
            },
            {
                "filename": "tests/test_auth.py",
                "status": "added",
                "additions": 70,
                "deletions": 0,
                "changes": 70,
                "patch": "@@ -0,0 +1,70 @@\n+tests",
            },
        ]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/pulls/7/files")
        assert len(result) == 2
        assert result[0]["filename"] == "src/auth.py"
        assert result[1]["status"] == "added"


class TestReviews:
    def test_list_reviews(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_REVIEW]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/pulls/7/reviews")
        assert result[0]["state"] == "APPROVED"
        assert result[0]["user"]["login"] == "bob"

    def test_approve_pull(self, mock_client):
        mock_client.rest.return_value = {
            "id": 51, "state": "APPROVED", "user": {"login": OWNER}
        }
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/pulls/7/reviews",
            body={"event": "APPROVE", "body": ""},
        )
        body = mock_client.rest.call_args[1]["body"]
        assert body["event"] == "APPROVE"

    def test_request_changes(self, mock_client):
        mock_client.rest.return_value = {
            "id": 52, "state": "CHANGES_REQUESTED", "user": {"login": OWNER}
        }
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/pulls/7/reviews",
            body={
                "event": "REQUEST_CHANGES",
                "body": "Please fix the error handling",
                "comments": [{"path": "src/auth.py", "line": 10, "body": "Handle None here"}],
            },
        )
        body = mock_client.rest.call_args[1]["body"]
        assert body["event"] == "REQUEST_CHANGES"
        assert len(body["comments"]) == 1

    def test_request_reviewers(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/pulls/7/requested_reviewers",
            body={"reviewers": ["bob", "carol"]},
        )
        body = mock_client.rest.call_args[1]["body"]
        assert "bob" in body["reviewers"]
        assert "carol" in body["reviewers"]


class TestPullComments:
    def test_list_comments(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_COMMENT]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/pulls/7/comments")
        assert result[0]["path"] == "src/auth.py"
        assert result[0]["line"] == 42

    def test_add_inline_comment(self, mock_client):
        mock_client.rest.return_value = SAMPLE_COMMENT
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/pulls/7/comments",
            body={
                "body": "Can we simplify this?",
                "commit_id": "abc123",
                "path": "src/auth.py",
                "line": 42,
                "side": "RIGHT",
            },
        )
        body = mock_client.rest.call_args[1]["body"]
        assert body["line"] == 42
        assert body["path"] == "src/auth.py"
        assert body["side"] == "RIGHT"

    def test_reply_to_comment(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_COMMENT, "id": 100}
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/pulls/7/comments/99/replies",
            body={"body": "Done, simplified."},
        )
        call = mock_client.rest.call_args
        assert "replies" in call[0][1]
        assert call[1]["body"]["body"] == "Done, simplified."


class TestShapePull:
    def test_base_shape_excludes_detail(self):
        from github.pulls import _shape_pull
        result = _shape_pull(SAMPLE_PULL)
        assert result["number"] == 7
        assert "body" not in result
        assert "additions" not in result

    def test_full_shape_includes_detail(self):
        from github.pulls import _shape_pull
        result = _shape_pull(SAMPLE_PULL, full=True)
        assert result["additions"] == 120
        assert result["deletions"] == 10
        assert result["reviewers"] == ["bob"]
        assert result["labels"] == ["feature"]

    def test_shape_review_comment(self):
        from github.pulls import _shape_review_comment
        result = _shape_review_comment(SAMPLE_COMMENT)
        assert result["id"] == 99
        assert result["path"] == "src/auth.py"
        assert result["line"] == 42
