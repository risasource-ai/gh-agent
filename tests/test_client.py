"""
tests/test_client.py

Tests for GitHubClient — error handling, response parsing, GitHubError.
Uses httpx mocking so no real network calls are made.
"""

import pytest
import httpx
from unittest.mock import patch, MagicMock
from github.client import GitHubClient, GitHubError, _extract_error


# ── GitHubError ───────────────────────────────────────────────────────

class TestGitHubError:
    def test_str_representation(self):
        e = GitHubError(status=404, message="Not Found", path="/repos/x/y")
        assert "404" in str(e)
        assert "Not Found" in str(e)
        assert "/repos/x/y" in str(e)

    def test_to_dict(self):
        e = GitHubError(status=422, message="Validation Failed", path="/user/repos")
        d = e.to_dict()
        assert d["error"] is True
        assert d["status"] == 422
        assert d["message"] == "Validation Failed"
        assert d["path"] == "/user/repos"

    def test_inherits_exception(self):
        e = GitHubError(status=500, message="Server Error", path="/test")
        assert isinstance(e, Exception)
        with pytest.raises(GitHubError):
            raise e


# ── _extract_error ────────────────────────────────────────────────────

class TestExtractError:
    def test_extracts_message_field(self):
        response = MagicMock()
        response.json.return_value = {"message": "Repository not found"}
        assert _extract_error(response) == "Repository not found"

    def test_falls_back_to_text(self):
        response = MagicMock()
        response.json.side_effect = ValueError("not json")
        response.text = "Internal Server Error"
        assert _extract_error(response) == "Internal Server Error"

    def test_falls_back_to_status(self):
        response = MagicMock()
        response.json.side_effect = ValueError("not json")
        response.text = ""
        response.status_code = 503
        assert "503" in _extract_error(response)


# ── GitHubClient ──────────────────────────────────────────────────────

class TestGitHubClient:
    def _make_client(self):
        return GitHubClient(token="test-token-123")

    def test_headers_set_correctly(self):
        client = self._make_client()
        assert "Authorization" in client._headers
        assert "Bearer test-token-123" in client._headers["Authorization"]
        assert "application/vnd.github+json" in client._headers["Accept"]
        assert "2022-11-28" in client._headers["X-GitHub-Api-Version"]

    def test_rest_success(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.content = b'{"login": "test"}'
        mock_response.json.return_value = {"login": "test"}

        with patch("httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.request.return_value = mock_response
            result = client.rest("GET", "/user")

        assert result == {"login": "test"}

    def test_rest_204_returns_success(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 204
        mock_response.content = b""

        with patch("httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.request.return_value = mock_response
            result = client.rest("DELETE", "/repos/x/y")

        assert result == {"success": True}

    def test_rest_raises_on_error(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}

        with patch("httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.request.return_value = mock_response
            with pytest.raises(GitHubError) as exc_info:
                client.rest("GET", "/repos/x/y")

        assert exc_info.value.status == 404
        assert "Not Found" in exc_info.value.message

    def test_rest_with_custom_accept(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.content = b'{"data": "ok"}'
        mock_response.json.return_value = {"data": "ok"}

        with patch("httpx.Client") as mock_httpx:
            ctx = mock_httpx.return_value.__enter__.return_value
            ctx.request.return_value = mock_response
            client.rest("GET", "/test", accept="application/vnd.github.diff")
            # verify the Accept header was overridden
            call_kwargs = ctx.request.call_args
            # headers passed to Client constructor
            headers_used = mock_httpx.call_args[1].get("headers", {})
            assert headers_used.get("Accept") == "application/vnd.github.diff"

    def test_rest_raw_returns_text(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.text = "diff --git a/file.py b/file.py"

        with patch("httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.request.return_value = mock_response
            result = client.rest_raw("GET", "/repos/x/y/pulls/1", accept="application/vnd.github.diff")

        assert result == "diff --git a/file.py b/file.py"

    def test_paginate_single_page(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [{"id": 1}, {"id": 2}]
        mock_response.links = {}  # no "next" link = last page

        with patch("httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.get.return_value = mock_response
            result = client.paginate("/user/repos")

        assert len(result) == 2
        assert result[0]["id"] == 1

    def test_paginate_respects_limit(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [{"id": i} for i in range(10)]
        mock_response.links = {}

        with patch("httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.get.return_value = mock_response
            result = client.paginate("/user/repos", limit=5)

        assert len(result) == 5

    def test_graphql_returns_data(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {"data": {"viewer": {"login": "test"}}}

        with patch("httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response
            result = client.graphql("{ viewer { login } }")

        assert result == {"viewer": {"login": "test"}}

    def test_graphql_raises_on_errors(self):
        client = self._make_client()
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "errors": [{"message": "Field 'xyz' doesn't exist"}]
        }

        with patch("httpx.Client") as mock_httpx:
            mock_httpx.return_value.__enter__.return_value.post.return_value = mock_response
            with pytest.raises(GitHubError) as exc_info:
                client.graphql("{ xyz }")

        assert "xyz" in exc_info.value.message
