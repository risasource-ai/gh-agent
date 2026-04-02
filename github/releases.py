"""
github/releases.py

Releases: create, list, update, delete, publish.
Assets: list, delete.
"""

from .client import GitHubClient, GitHubError


def register(mcp, client: GitHubClient, owner: str):

    @mcp.tool()
    def list_releases(repo: str, limit: int = 20) -> list[dict]:
        """
        List releases in a repository.

        repo: repository name
        limit: max releases to return
        """
        try:
            releases = client.paginate(
                f"/repos/{owner}/{repo}/releases", limit=limit
            )
            return [_shape_release(r) for r in releases]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_release(repo: str, release_id: int) -> dict:
        """
        Get a specific release by ID.

        repo: repository name
        release_id: release ID number
        """
        try:
            r = client.rest("GET", f"/repos/{owner}/{repo}/releases/{release_id}")
            return _shape_release(r, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def get_latest_release(repo: str) -> dict:
        """
        Get the latest published release.

        repo: repository name
        """
        try:
            r = client.rest("GET", f"/repos/{owner}/{repo}/releases/latest")
            return _shape_release(r, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def get_release_by_tag(repo: str, tag: str) -> dict:
        """
        Get a release by its tag name.

        repo: repository name
        tag: tag name (e.g. "v1.0.0")
        """
        try:
            r = client.rest("GET", f"/repos/{owner}/{repo}/releases/tags/{tag}")
            return _shape_release(r, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def create_release(
        repo: str,
        tag_name: str,
        name: str = "",
        body: str = "",
        draft: bool = False,
        prerelease: bool = False,
        target_commitish: str = "",
        generate_release_notes: bool = False,
    ) -> dict:
        """
        Create a new release.

        repo: repository name
        tag_name: tag to create or use (e.g. "v1.0.0")
        name: release title (defaults to tag name)
        body: release description / changelog (markdown)
        draft: create as draft — not publicly visible until published
        prerelease: mark as pre-release
        target_commitish: branch or commit SHA to tag (defaults to default branch)
        generate_release_notes: auto-generate release notes from merged PRs
        """
        try:
            payload: dict = {
                "tag_name": tag_name,
                "name": name or tag_name,
                "body": body,
                "draft": draft,
                "prerelease": prerelease,
                "generate_release_notes": generate_release_notes,
            }
            if target_commitish:
                payload["target_commitish"] = target_commitish

            r = client.rest(
                "POST", f"/repos/{owner}/{repo}/releases", body=payload
            )
            return _shape_release(r, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def update_release(
        repo: str,
        release_id: int,
        tag_name: str = "",
        name: str = "",
        body: str = "",
        draft: bool | None = None,
        prerelease: bool | None = None,
    ) -> dict:
        """
        Update an existing release.

        repo: repository name
        release_id: release ID number
        Pass only the fields you want to change.
        """
        try:
            payload: dict = {}
            if tag_name:
                payload["tag_name"] = tag_name
            if name:
                payload["name"] = name
            if body:
                payload["body"] = body
            if draft is not None:
                payload["draft"] = draft
            if prerelease is not None:
                payload["prerelease"] = prerelease

            r = client.rest(
                "PATCH",
                f"/repos/{owner}/{repo}/releases/{release_id}",
                body=payload,
            )
            return _shape_release(r, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def publish_release(repo: str, release_id: int) -> dict:
        """
        Publish a draft release (makes it public).

        repo: repository name
        release_id: release ID number
        """
        try:
            r = client.rest(
                "PATCH",
                f"/repos/{owner}/{repo}/releases/{release_id}",
                body={"draft": False},
            )
            return _shape_release(r)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def delete_release(repo: str, release_id: int) -> dict:
        """
        Delete a release. Does not delete the associated tag.

        repo: repository name
        release_id: release ID number
        """
        try:
            client.rest("DELETE", f"/repos/{owner}/{repo}/releases/{release_id}")
            return {"success": True, "deleted_release": release_id}
        except GitHubError as e:
            return e.to_dict()

    # ── assets ────────────────────────────────────────────────────────

    @mcp.tool()
    def list_release_assets(repo: str, release_id: int) -> list[dict]:
        """
        List assets attached to a release.

        repo: repository name
        release_id: release ID number
        """
        try:
            assets = client.paginate(
                f"/repos/{owner}/{repo}/releases/{release_id}/assets"
            )
            return [_shape_asset(a) for a in assets]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def delete_release_asset(repo: str, asset_id: int) -> dict:
        """
        Delete a release asset.

        repo: repository name
        asset_id: asset ID number
        """
        try:
            client.rest(
                "DELETE",
                f"/repos/{owner}/{repo}/releases/assets/{asset_id}",
            )
            return {"success": True, "deleted_asset": asset_id}
        except GitHubError as e:
            return e.to_dict()


# ── shape helpers ─────────────────────────────────────────────────────

def _shape_release(r: dict, full: bool = False) -> dict:
    base = {
        "id": r["id"],
        "tag_name": r["tag_name"],
        "name": r.get("name", ""),
        "draft": r.get("draft", False),
        "prerelease": r.get("prerelease", False),
        "created_at": r.get("created_at"),
        "published_at": r.get("published_at"),
        "url": r.get("html_url"),
        "assets_count": len(r.get("assets", [])),
        "author": r["author"]["login"] if r.get("author") else None,
    }
    if full:
        base.update({
            "body": r.get("body", ""),
            "assets": [_shape_asset(a) for a in r.get("assets", [])],
            "tarball_url": r.get("tarball_url"),
            "zipball_url": r.get("zipball_url"),
        })
    return base


def _shape_asset(a: dict) -> dict:
    return {
        "id": a["id"],
        "name": a["name"],
        "size_mb": round(a["size"] / 1024 / 1024, 2),
        "content_type": a.get("content_type", ""),
        "state": a.get("state", ""),
        "download_count": a.get("download_count", 0),
        "created_at": a.get("created_at"),
        "download_url": a.get("browser_download_url"),
    }
