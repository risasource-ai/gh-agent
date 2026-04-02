"""
tests/conftest.py

Shared fixtures. Every test gets a MockClient and a real FastMCP server
with all modules registered — no real GitHub calls, no tokens needed.
"""

import pytest
from unittest.mock import MagicMock
from mcp.server.fastmcp import FastMCP
from github.client import GitHubClient, GitHubError


# ── mock client ───────────────────────────────────────────────────────

class MockClient:
    """
    Drop-in replacement for GitHubClient.
    Tests control what rest(), paginate(), graphql(), rest_raw() return
    by setting mock_client.rest.return_value etc.
    """
    def __init__(self):
        self.rest = MagicMock()
        self.paginate = MagicMock()
        self.graphql = MagicMock()
        self.rest_raw = MagicMock()
        self.whoami = MagicMock(return_value={
            "login": "test-owner",
            "name": "Test Owner",
            "email": "test@example.com",
            "public_repos": 5,
            "total_private_repos": 2,
            "followers": 10,
            "html_url": "https://github.com/test-owner",
            "bio": "testing",
        })


OWNER = "test-owner"


@pytest.fixture
def mock_client():
    return MockClient()


@pytest.fixture
def mcp_server(mock_client):
    """
    A FastMCP server with all modules registered against the mock client.
    Tests call tools by invoking the registered functions directly.
    """
    mcp = FastMCP("gh-mcp-test")

    from github import repos, files, pulls, issues, actions, releases, search
    repos.register(mcp, mock_client, OWNER)
    files.register(mcp, mock_client, OWNER)
    pulls.register(mcp, mock_client, OWNER)
    issues.register(mcp, mock_client, OWNER)
    actions.register(mcp, mock_client, OWNER)
    releases.register(mcp, mock_client, OWNER)
    search.register(mcp, mock_client, OWNER)

    return mcp


# ── helpers ───────────────────────────────────────────────────────────

def make_error(status: int = 404, message: str = "Not Found", path: str = "/test") -> GitHubError:
    return GitHubError(status=status, message=message, path=path)


def github_error_side_effect(status: int = 404, message: str = "Not Found"):
    """Use as side_effect= to make a mock raise GitHubError."""
    raise GitHubError(status=status, message=message, path="/test")
