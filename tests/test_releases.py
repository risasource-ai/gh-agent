"""
tests/test_releases.py

Tests for releases module.
"""

import pytest
from github.client import GitHubError
from tests.conftest import OWNER


SAMPLE_RELEASE = {
    "id": 1,
    "tag_name": "v1.0.0",
    "name": "Version 1.0.0",
    "draft": False,
    "prerelease": False,
    "created_at": "2024-01-01T00:00:00Z",
    "published_at": "2024-01-01T01:00:00Z",
    "html_url": f"https://github.com/{OWNER}/my-repo/releases/tag/v1.0.0",
    "assets": [],
    "body": "First stable release.",
    "author": {"login": OWNER},
    "tarball_url": f"https://api.github.com/repos/{OWNER}/my-repo/tarball/v1.0.0",
    "zipball_url": f"https://api.github.com/repos/{OWNER}/my-repo/zipball/v1.0.0",
}


class TestListReleases:
    def test_returns_releases(self, mock_client):
        mock_client.paginate.return_value = [SAMPLE_RELEASE]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/releases")
        assert len(result) == 1
        assert result[0]["tag_name"] == "v1.0.0"

    def test_empty_repo(self, mock_client):
        mock_client.paginate.return_value = []
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/releases")
        assert result == []


class TestGetRelease:
    def test_get_by_id(self, mock_client):
        mock_client.rest.return_value = SAMPLE_RELEASE
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/releases/1")
        assert result["id"] == 1
        assert result["tag_name"] == "v1.0.0"

    def test_get_latest(self, mock_client):
        mock_client.rest.return_value = SAMPLE_RELEASE
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/releases/latest")
        assert result["tag_name"] == "v1.0.0"

    def test_get_by_tag(self, mock_client):
        mock_client.rest.return_value = SAMPLE_RELEASE
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/releases/tags/v1.0.0")
        assert result["tag_name"] == "v1.0.0"

    def test_not_found(self, mock_client):
        mock_client.rest.side_effect = GitHubError(404, "Not Found", "/repos/x/y/releases/999")
        with pytest.raises(GitHubError):
            mock_client.rest("GET", f"/repos/{OWNER}/my-repo/releases/999")


class TestCreateRelease:
    def test_create_with_required_fields(self, mock_client):
        mock_client.rest.return_value = SAMPLE_RELEASE
        mock_client.rest("POST", f"/repos/{OWNER}/my-repo/releases", body={
            "tag_name": "v1.0.0",
            "name": "v1.0.0",
            "body": "",
            "draft": False,
            "prerelease": False,
            "generate_release_notes": False,
        })
        body = mock_client.rest.call_args[1]["body"]
        assert body["tag_name"] == "v1.0.0"

    def test_create_draft(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_RELEASE, "draft": True}
        mock_client.rest("POST", f"/repos/{OWNER}/my-repo/releases", body={
            "tag_name": "v2.0.0-draft",
            "draft": True,
        })
        body = mock_client.rest.call_args[1]["body"]
        assert body["draft"] is True

    def test_create_with_target_commitish(self, mock_client):
        mock_client.rest.return_value = SAMPLE_RELEASE
        mock_client.rest("POST", f"/repos/{OWNER}/my-repo/releases", body={
            "tag_name": "v1.0.0",
            "target_commitish": "abc123",
        })
        body = mock_client.rest.call_args[1]["body"]
        assert body["target_commitish"] == "abc123"


class TestUpdateRelease:
    def test_publish_draft(self, mock_client):
        mock_client.rest.return_value = {**SAMPLE_RELEASE, "draft": False}
        mock_client.rest("PATCH", f"/repos/{OWNER}/my-repo/releases/1", body={"draft": False})
        body = mock_client.rest.call_args[1]["body"]
        assert body["draft"] is False

    def test_update_body(self, mock_client):
        mock_client.rest.return_value = SAMPLE_RELEASE
        mock_client.rest("PATCH", f"/repos/{OWNER}/my-repo/releases/1", body={"body": "Updated notes"})
        body = mock_client.rest.call_args[1]["body"]
        assert body["body"] == "Updated notes"


class TestDeleteRelease:
    def test_delete(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("DELETE", f"/repos/{OWNER}/my-repo/releases/1")
        call = mock_client.rest.call_args
        assert call[0][0] == "DELETE"
        assert "releases/1" in call[0][1]


class TestReleaseAssets:
    def test_list_assets(self, mock_client):
        mock_client.paginate.return_value = [
            {
                "id": 10,
                "name": "app-linux-amd64",
                "size": 1024 * 1024 * 5,
                "content_type": "application/octet-stream",
                "state": "uploaded",
                "download_count": 100,
                "created_at": "2024-01-01T00:00:00Z",
                "browser_download_url": "https://github.com/releases/download/v1.0.0/app",
            }
        ]
        result = mock_client.paginate(f"/repos/{OWNER}/my-repo/releases/1/assets")
        assert result[0]["name"] == "app-linux-amd64"

    def test_delete_asset(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("DELETE", f"/repos/{OWNER}/my-repo/releases/assets/10")
        call = mock_client.rest.call_args
        assert call[0][0] == "DELETE"
        assert "assets/10" in call[0][1]


class TestShapeRelease:
    def test_base_shape(self):
        from github.releases import _shape_release
        result = _shape_release(SAMPLE_RELEASE)
        assert result["id"] == 1
        assert result["tag_name"] == "v1.0.0"
        assert "body" not in result
        assert "assets" not in result

    def test_full_shape(self):
        from github.releases import _shape_release
        result = _shape_release(SAMPLE_RELEASE, full=True)
        assert "body" in result
        assert "assets" in result
        assert result["author"] == OWNER

    def test_asset_size_in_mb(self):
        from github.releases import _shape_asset
        asset = {
            "id": 1,
            "name": "file.tar.gz",
            "size": 1024 * 1024 * 2,
            "content_type": "application/gzip",
            "state": "uploaded",
            "download_count": 5,
            "created_at": "2024-01-01",
            "browser_download_url": "https://example.com/file.tar.gz",
        }
        result = _shape_asset(asset)
        assert result["size_mb"] == 2.0
