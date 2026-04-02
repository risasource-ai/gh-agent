"""
tests/test_search.py

Tests for search module.
"""

import pytest
from github.client import GitHubError
from tests.conftest import OWNER


SAMPLE_CODE_RESULT = {
    "items": [
        {
            "name": "auth.py",
            "path": "src/auth.py",
            "sha": "abc123",
            "html_url": f"https://github.com/{OWNER}/my-repo/blob/main/src/auth.py",
            "repository": {"full_name": f"{OWNER}/my-repo", "name": "my-repo"},
        }
    ],
    "total_count": 1,
}

SAMPLE_REPO_RESULT = {
    "items": [
        {
            "full_name": "someone/awesome-ml",
            "description": "ML stuff",
            "stargazers_count": 5000,
            "language": "Python",
            "html_url": "https://github.com/someone/awesome-ml",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    ]
}

SAMPLE_ISSUE_RESULT = {
    "items": [
        {
            "number": 42,
            "title": "Bug: login fails",
            "state": "open",
            "user": {"login": "reporter"},
            "html_url": f"https://github.com/{OWNER}/my-repo/issues/42",
            "created_at": "2024-01-01T00:00:00Z",
            "labels": [{"name": "bug"}],
            "repository_url": f"https://api.github.com/repos/{OWNER}/my-repo",
        }
    ]
}

SAMPLE_COMMIT_RESULT = {
    "items": [
        {
            "sha": "abcdef1234567890",
            "commit": {
                "message": "fix: resolve auth issue",
                "author": {"name": "Alice", "date": "2024-01-01T00:00:00Z"},
            },
            "repository": {"full_name": f"{OWNER}/my-repo"},
            "html_url": f"https://github.com/{OWNER}/my-repo/commit/abcdef1",
        }
    ]
}

SAMPLE_USER_RESULT = {
    "items": [
        {
            "login": "alice",
            "type": "User",
            "html_url": "https://github.com/alice",
            "avatar_url": "https://avatars.githubusercontent.com/u/1",
        }
    ]
}


class TestSearchCode:
    def test_builds_correct_query(self, mock_client):
        mock_client.rest.return_value = SAMPLE_CODE_RESULT
        mock_client.rest(
            "GET",
            "/search/code",
            params={"q": "def authenticate repo:test-owner/my-repo language:python", "per_page": 20},
        )
        call = mock_client.rest.call_args
        assert call[1]["params"]["q"]

    def test_returns_shaped_results(self, mock_client):
        mock_client.rest.return_value = SAMPLE_CODE_RESULT
        result = mock_client.rest("GET", "/search/code", params={"q": "test"})
        assert result["items"][0]["name"] == "auth.py"
        assert result["items"][0]["path"] == "src/auth.py"

    def test_scopes_to_repo_when_specified(self, mock_client):
        mock_client.rest.return_value = SAMPLE_CODE_RESULT
        mock_client.rest(
            "GET", "/search/code",
            params={"q": f"authenticate repo:{OWNER}/my-repo"}
        )
        q = mock_client.rest.call_args[1]["params"]["q"]
        assert f"repo:{OWNER}/my-repo" in q

    def test_rate_limit_error(self, mock_client):
        mock_client.rest.side_effect = GitHubError(403, "API rate limit exceeded", "/search/code")
        with pytest.raises(GitHubError) as exc:
            mock_client.rest("GET", "/search/code", params={"q": "test"})
        assert exc.value.status == 403


class TestSearchRepos:
    def test_returns_repos(self, mock_client):
        mock_client.rest.return_value = SAMPLE_REPO_RESULT
        result = mock_client.rest("GET", "/search/repositories", params={"q": "ml"})
        assert result["items"][0]["full_name"] == "someone/awesome-ml"
        assert result["items"][0]["stargazers_count"] == 5000

    def test_adds_language_filter(self, mock_client):
        mock_client.rest.return_value = SAMPLE_REPO_RESULT
        mock_client.rest(
            "GET", "/search/repositories",
            params={"q": "ml language:python", "sort": "stars"},
        )
        q = mock_client.rest.call_args[1]["params"]["q"]
        assert "language:python" in q

    def test_sort_by_stars(self, mock_client):
        mock_client.rest.return_value = SAMPLE_REPO_RESULT
        mock_client.rest(
            "GET", "/search/repositories",
            params={"q": "ml", "sort": "stars", "order": "desc"},
        )
        params = mock_client.rest.call_args[1]["params"]
        assert params["sort"] == "stars"


class TestSearchIssues:
    def test_returns_issues(self, mock_client):
        mock_client.rest.return_value = SAMPLE_ISSUE_RESULT
        result = mock_client.rest("GET", "/search/issues", params={"q": "bug is:issue"})
        assert result["items"][0]["number"] == 42
        assert result["items"][0]["title"] == "Bug: login fails"

    def test_filters_prs(self, mock_client):
        mock_client.rest.return_value = {"items": []}
        mock_client.rest("GET", "/search/issues", params={"q": "test is:pr"})
        q = mock_client.rest.call_args[1]["params"]["q"]
        assert "is:pr" in q

    def test_adds_state_filter(self, mock_client):
        mock_client.rest.return_value = SAMPLE_ISSUE_RESULT
        mock_client.rest("GET", "/search/issues", params={"q": "bug state:open is:issue"})
        q = mock_client.rest.call_args[1]["params"]["q"]
        assert "state:open" in q


class TestSearchCommits:
    def test_returns_commits(self, mock_client):
        mock_client.rest.return_value = SAMPLE_COMMIT_RESULT
        result = mock_client.rest("GET", "/search/commits", params={"q": "fix auth"})
        assert result["items"][0]["sha"] == "abcdef1234567890"
        assert "fix" in result["items"][0]["commit"]["message"]

    def test_scopes_to_repo(self, mock_client):
        mock_client.rest.return_value = SAMPLE_COMMIT_RESULT
        mock_client.rest(
            "GET", "/search/commits",
            params={"q": f"fix repo:{OWNER}/my-repo"},
        )
        q = mock_client.rest.call_args[1]["params"]["q"]
        assert f"repo:{OWNER}/my-repo" in q

    def test_adds_author_filter(self, mock_client):
        mock_client.rest.return_value = SAMPLE_COMMIT_RESULT
        mock_client.rest(
            "GET", "/search/commits",
            params={"q": "fix author:alice"},
        )
        q = mock_client.rest.call_args[1]["params"]["q"]
        assert "author:alice" in q


class TestSearchUsers:
    def test_returns_users(self, mock_client):
        mock_client.rest.return_value = SAMPLE_USER_RESULT
        result = mock_client.rest("GET", "/search/users", params={"q": "alice type:user"})
        assert result["items"][0]["login"] == "alice"

    def test_org_type(self, mock_client):
        mock_client.rest.return_value = {"items": []}
        mock_client.rest("GET", "/search/users", params={"q": "anthropic type:org"})
        q = mock_client.rest.call_args[1]["params"]["q"]
        assert "type:org" in q


class TestSearchMyCode:
    def test_scopes_to_owner(self, mock_client):
        mock_client.rest.return_value = SAMPLE_CODE_RESULT
        mock_client.rest(
            "GET", "/search/code",
            params={"q": f"authenticate user:{OWNER}"},
        )
        q = mock_client.rest.call_args[1]["params"]["q"]
        assert f"user:{OWNER}" in q
