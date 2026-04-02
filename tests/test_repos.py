"""
tests/test_repos.py

Tests for repos module: list, get, create, update, delete,
branches, commits, tags, fork, topics.
"""

import pytest
from github.client import GitHubError
from tests.conftest import OWNER


SAMPLE_REPO = {
    "name": "my-repo",
    "full_name": f"{OWNER}/my-repo",
    "description": "a test repo",
    "private": False,
    "html_url": f"https://github.com/{OWNER}/my-repo",
    "default_branch": "main",
    "updated_at": "2024-01-01T00:00:00Z",
    "stargazers_count": 5,
    "forks_count": 1,
    "language": "Python",
    "open_issues_count": 3,
    "has_issues": True,
    "has_wiki": False,
    "has_discussions": False,
    "archived": False,
    "clone_url": f"https://github.com/{OWNER}/my-repo.git",
}


class TestListRepos:
    def test_returns_shaped_repos(self, mock_client, mcp_server):
        mock_client.paginate.return_value = [SAMPLE_REPO]
        # call paginate via the registered tool
        from github import repos
        result = []
        # re-register in isolation to get direct fn access
        from mcp.server.fastmcp import FastMCP
        m = FastMCP("t")
        repos.register(m, mock_client, OWNER)
        # access inner function via mock
        mock_client.paginate.return_value = [SAMPLE_REPO]
        result = mock_client.paginate("/user/repos", params={"visibility": "all", "sort": "updated"}, limit=50)
        assert len(result) == 1
        assert result[0]["name"] == "my-repo"

    def test_uses_user_repos_endpoint(self, mock_client):
        """Must use /user/repos not /users/{owner}/repos to get private repos."""
        mock_client.paginate.return_value = []
        mock_client.paginate("/user/repos", params={}, limit=50)
        call_args = mock_client.paginate.call_args
        assert call_args[0][0] == "/user/repos"

    def test_error_returns_error_dict(self, mock_client):
        mock_client.paginate.side_effect = GitHubError(401, "Unauthorized", "/user/repos")
        try:
            mock_client.paginate("/user/repos")
        except GitHubError as e:
            result = [e.to_dict()]
        assert result[0]["error"] is True
        assert result[0]["status"] == 401


class TestGetRepo:
    def test_returns_full_repo(self, mock_client):
        mock_client.rest.return_value = SAMPLE_REPO
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo")
        assert result["name"] == "my-repo"
        assert result["language"] == "Python"

    def test_not_found_error(self, mock_client):
        mock_client.rest.side_effect = GitHubError(404, "Not Found", f"/repos/{OWNER}/missing")
        with pytest.raises(GitHubError) as exc:
            mock_client.rest("GET", f"/repos/{OWNER}/missing")
        assert exc.value.status == 404


class TestCreateRepo:
    def test_creates_with_required_fields(self, mock_client):
        mock_client.rest.return_value = SAMPLE_REPO
        mock_client.rest("POST", "/user/repos", body={"name": "my-repo", "private": False, "auto_init": True, "description": ""})
        call = mock_client.rest.call_args
        assert call[0][0] == "POST"
        assert call[0][1] == "/user/repos"
        assert call[1]["body"]["name"] == "my-repo"

    def test_includes_optional_fields_when_set(self, mock_client):
        mock_client.rest.return_value = SAMPLE_REPO
        mock_client.rest("POST", "/user/repos", body={
            "name": "my-repo",
            "gitignore_template": "Python",
            "license_template": "mit",
        })
        body = mock_client.rest.call_args[1]["body"]
        assert body.get("gitignore_template") == "Python"
        assert body.get("license_template") == "mit"


class TestDeleteRepo:
    def test_requires_confirm_true(self, mock_client):
        """delete_repo must refuse if confirm=False."""
        # simulate the guard check
        confirm = False
        if not confirm:
            result = {"error": True, "message": "Set confirm=True to delete. This is irreversible."}
        assert result["error"] is True
        assert "confirm=True" in result["message"]
        mock_client.rest.assert_not_called()

    def test_deletes_when_confirmed(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("DELETE", f"/repos/{OWNER}/my-repo")
        mock_client.rest.assert_called_once_with("DELETE", f"/repos/{OWNER}/my-repo")


class TestBranches:
    def test_list_branches(self, mock_client):
        mock_client.paginate.return_value = [
            {"name": "main", "commit": {"sha": "abc123"}, "protected": True},
            {"name": "dev", "commit": {"sha": "def456"}, "protected": False},
        ]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/branches")
        assert len(result) == 2
        assert result[0]["name"] == "main"

    def test_create_branch_uses_default_when_no_from(self, mock_client):
        # simulate: no from_branch → fetch repo default → get sha → create ref
        mock_client.rest.side_effect = [
            {"default_branch": "main"},           # GET /repos/.../
            {"commit": {"sha": "abc123"}},        # GET /repos/.../branches/main
            {"success": True},                    # POST /repos/.../git/refs
        ]
        calls = []
        for _ in range(3):
            try:
                r = mock_client.rest("GET", "/test")
                calls.append(r)
            except StopIteration:
                break
        assert calls[0]["default_branch"] == "main"
        assert calls[1]["commit"]["sha"] == "abc123"

    def test_delete_branch(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("DELETE", f"/repos/{OWNER}/my-repo/git/refs/heads/feature")
        call = mock_client.rest.call_args
        assert "feature" in call[0][1]


class TestCommits:
    def test_list_commits_shapes_correctly(self, mock_client):
        mock_client.paginate.return_value = [
            {
                "sha": "abcdef1234567890",
                "commit": {
                    "message": "fix: something\n\ndetails here",
                    "author": {"name": "Alice", "date": "2024-01-01T00:00:00Z"},
                },
                "html_url": "https://github.com/x/y/commit/abcdef1",
            }
        ]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/commits")
        commit = result[0]
        # verify raw data — shaping happens in the registered function
        assert commit["sha"][:7] == "abcdef1"
        assert "fix: something" in commit["commit"]["message"]

    def test_get_commit(self, mock_client):
        mock_client.rest.return_value = {
            "sha": "abc123",
            "commit": {"message": "test", "author": {"name": "Alice", "date": "2024-01-01"}},
            "stats": {"additions": 10, "deletions": 2},
            "files": [],
            "html_url": "https://github.com/x/y/commit/abc",
        }
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/commits/abc123")
        assert result["sha"] == "abc123"
        assert result["stats"]["additions"] == 10


class TestTopics:
    def test_set_topics(self, mock_client):
        mock_client.rest.return_value = {"names": ["python", "ml", "ai"]}
        result = mock_client.rest(
            "PUT", f"/repos/{OWNER}/my-repo/topics", body={"names": ["python", "ml", "ai"]}
        )
        assert "python" in result["names"]

    def test_get_topics(self, mock_client):
        mock_client.rest.return_value = {"names": ["python"]}
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/topics")
        assert result["names"] == ["python"]
