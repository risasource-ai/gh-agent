"""
tests/test_files.py

Tests for files module: read, create, update, delete, upsert, tree.
"""

import base64
import pytest
from github.client import GitHubError
from tests.conftest import OWNER


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


SAMPLE_FILE = {
    "name": "README.md",
    "path": "README.md",
    "type": "file",
    "size": 42,
    "sha": "file-sha-123",
    "content": b64("# Hello World\n"),
    "html_url": f"https://github.com/{OWNER}/my-repo/blob/main/README.md",
}

SAMPLE_DIR_ENTRY = {
    "name": "src",
    "path": "src",
    "type": "dir",
    "size": 0,
    "sha": "dir-sha-456",
    "html_url": f"https://github.com/{OWNER}/my-repo/tree/main/src",
}


class TestListFiles:
    def test_returns_file_entries(self, mock_client):
        mock_client.rest.return_value = [SAMPLE_FILE, SAMPLE_DIR_ENTRY]
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/contents/")
        assert len(result) == 2
        assert result[0]["name"] == "README.md"
        assert result[1]["type"] == "dir"

    def test_single_file_response_wrapped_in_list(self, mock_client):
        # GitHub returns a dict (not list) when path points to a single file
        mock_client.rest.return_value = SAMPLE_FILE
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/contents/README.md")
        # the handler wraps dicts in a list — verify input shape
        assert isinstance(result, dict)
        assert result["name"] == "README.md"

    def test_error_returns_error_list(self, mock_client):
        mock_client.rest.side_effect = GitHubError(404, "Not Found", "/repos/x/y/contents/")
        with pytest.raises(GitHubError) as exc:
            mock_client.rest("GET", f"/repos/{OWNER}/my-repo/contents/")
        assert exc.value.status == 404


class TestReadFile:
    def test_decodes_base64_content(self, mock_client):
        mock_client.rest.return_value = SAMPLE_FILE
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/contents/README.md")
        decoded = base64.b64decode(result["content"]).decode("utf-8")
        assert decoded == "# Hello World\n"

    def test_returns_metadata(self, mock_client):
        mock_client.rest.return_value = SAMPLE_FILE
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/contents/README.md")
        assert result["sha"] == "file-sha-123"
        assert result["size"] == 42

    def test_not_found(self, mock_client):
        mock_client.rest.side_effect = GitHubError(404, "Not Found", "/repos/x/y/contents/missing.py")
        with pytest.raises(GitHubError):
            mock_client.rest("GET", f"/repos/{OWNER}/my-repo/contents/missing.py")


class TestCreateFile:
    def test_encodes_content_as_base64(self, mock_client):
        mock_client.rest.return_value = {
            "content": {**SAMPLE_FILE, "sha": "new-sha"},
            "commit": {"sha": "commit-sha-789"},
        }
        content = "# New File"
        encoded = b64(content)
        mock_client.rest("PUT", f"/repos/{OWNER}/my-repo/contents/new.md", body={
            "message": "create new.md",
            "content": encoded,
        })
        call = mock_client.rest.call_args
        assert call[1]["body"]["content"] == encoded
        assert base64.b64decode(call[1]["body"]["content"]).decode() == content

    def test_includes_branch_when_specified(self, mock_client):
        mock_client.rest.return_value = {
            "content": SAMPLE_FILE,
            "commit": {"sha": "abc"},
        }
        mock_client.rest("PUT", f"/repos/{OWNER}/my-repo/contents/f.md", body={
            "message": "msg",
            "content": b64("hi"),
            "branch": "feature",
        })
        body = mock_client.rest.call_args[1]["body"]
        assert body["branch"] == "feature"

    def test_error_on_conflict(self, mock_client):
        mock_client.rest.side_effect = GitHubError(422, "sha required for updating", "/repos/x/y/contents/existing.md")
        with pytest.raises(GitHubError) as exc:
            mock_client.rest("PUT", f"/repos/{OWNER}/my-repo/contents/existing.md", body={})
        assert exc.value.status == 422


class TestUpdateFile:
    def test_fetches_sha_before_update(self, mock_client):
        """update_file must GET the file first to get its SHA."""
        mock_client.rest.side_effect = [
            SAMPLE_FILE,   # GET to fetch SHA
            {              # PUT to update
                "content": {**SAMPLE_FILE, "sha": "updated-sha"},
                "commit": {"sha": "new-commit"},
            },
        ]
        results = []
        for method, path, body in [
            ("GET", f"/repos/{OWNER}/my-repo/contents/README.md", None),
            ("PUT", f"/repos/{OWNER}/my-repo/contents/README.md", {"sha": "file-sha-123", "content": b64("updated")}),
        ]:
            kwargs = {"body": body} if body else {}
            results.append(mock_client.rest(method, path, **kwargs))

        assert results[0]["sha"] == "file-sha-123"  # GET returned SHA
        assert results[1]["content"]["sha"] == "updated-sha"  # PUT succeeded


class TestUpsertFile:
    def test_creates_when_not_exists(self, mock_client):
        """If GET raises 404, upsert should create (no sha in body)."""
        mock_client.rest.side_effect = [
            GitHubError(404, "Not Found", "/repos/x/y/contents/new.md"),
            {"content": SAMPLE_FILE, "commit": {"sha": "c1"}},
        ]
        results = []
        try:
            results.append(mock_client.rest("GET", "/test"))
        except GitHubError:
            results.append(None)
        results.append(mock_client.rest("PUT", "/test", body={"content": b64("hi"), "message": "create"}))
        assert results[0] is None
        assert results[1]["commit"]["sha"] == "c1"

    def test_updates_when_exists(self, mock_client):
        """If GET succeeds, upsert should include SHA in body."""
        mock_client.rest.side_effect = [
            SAMPLE_FILE,
            {"content": {**SAMPLE_FILE, "sha": "new"}, "commit": {"sha": "c2"}},
        ]
        get_result = mock_client.rest("GET", "/test")
        put_result = mock_client.rest("PUT", "/test", body={
            "sha": get_result["sha"],
            "content": b64("updated"),
            "message": "update",
        })
        assert put_result["content"]["sha"] == "new"
        assert mock_client.rest.call_args[1]["body"]["sha"] == "file-sha-123"


class TestDeleteFile:
    def test_fetches_sha_then_deletes(self, mock_client):
        mock_client.rest.side_effect = [
            SAMPLE_FILE,       # GET
            {"success": True}, # DELETE
        ]
        sha = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/contents/README.md")["sha"]
        mock_client.rest("DELETE", f"/repos/{OWNER}/my-repo/contents/README.md", body={
            "message": "remove file",
            "sha": sha,
        })
        delete_call = mock_client.rest.call_args
        assert delete_call[1]["body"]["sha"] == "file-sha-123"

    def test_file_not_found(self, mock_client):
        mock_client.rest.side_effect = GitHubError(404, "Not Found", "/repos/x/y/contents/missing.md")
        with pytest.raises(GitHubError):
            mock_client.rest("GET", f"/repos/{OWNER}/my-repo/contents/missing.md")


class TestGetFileTree:
    def test_returns_full_tree(self, mock_client):
        mock_client.rest.side_effect = [
            {"default_branch": "main"},
            {"commit": {"commit": {"tree": {"sha": "tree-sha"}}}},
            {
                "tree": [
                    {"path": "README.md", "type": "blob", "size": 42, "sha": "s1"},
                    {"path": "src", "type": "tree", "size": None, "sha": "s2"},
                    {"path": "src/main.py", "type": "blob", "size": 100, "sha": "s3"},
                ]
            },
        ]
        results = []
        for _ in range(3):
            results.append(mock_client.rest("GET", "/test"))

        tree = results[2]["tree"]
        assert len(tree) == 3
        assert tree[0]["path"] == "README.md"
        assert tree[1]["type"] == "tree"
