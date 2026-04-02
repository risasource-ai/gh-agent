"""
github/files.py

File operations: read, create, update, delete, upsert, list tree.
Handles base64 encoding/decoding transparently.
"""

import base64
from .client import GitHubClient, GitHubError


def register(mcp, client: GitHubClient, owner: str):

    @mcp.tool()
    def list_files(repo: str, path: str = "", branch: str = "") -> list[dict]:
        """
        List files and directories at a path in a repository.

        repo: repository name
        path: directory path (empty string = root)
        branch: branch name (defaults to default branch)
        """
        try:
            params = {}
            if branch:
                params["ref"] = branch
            contents = client.rest(
                "GET",
                f"/repos/{owner}/{repo}/contents/{path}",
                params=params or None,
            )
            if isinstance(contents, dict):
                contents = [contents]
            return [
                {
                    "name": c["name"],
                    "path": c["path"],
                    "type": c["type"],
                    "size": c.get("size", 0),
                    "sha": c["sha"],
                    "url": c.get("html_url"),
                }
                for c in contents
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def read_file(repo: str, path: str, branch: str = "") -> dict:
        """
        Read the contents of a file.

        repo: repository name
        path: file path in the repo
        branch: branch name (defaults to default branch)
        """
        try:
            params = {}
            if branch:
                params["ref"] = branch
            f = client.rest(
                "GET",
                f"/repos/{owner}/{repo}/contents/{path}",
                params=params or None,
            )
            if isinstance(f, list) or f.get("type") != "file":
                return {"error": True, "message": f"{path} is not a file"}

            content = base64.b64decode(f["content"]).decode("utf-8")
            return {
                "path": f["path"],
                "content": content,
                "size": f["size"],
                "sha": f["sha"],
                "url": f.get("html_url"),
                "encoding": "utf-8",
            }
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def create_file(
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "",
    ) -> dict:
        """
        Create a new file in a repository.

        repo: repository name
        path: file path (e.g. "src/main.py")
        content: file content as a string
        message: commit message
        branch: branch to commit to (defaults to default branch)
        """
        try:
            body: dict = {
                "message": message,
                "content": base64.b64encode(content.encode()).decode(),
            }
            if branch:
                body["branch"] = branch

            result = client.rest(
                "PUT",
                f"/repos/{owner}/{repo}/contents/{path}",
                body=body,
            )
            return {
                "success": True,
                "action": "created",
                "path": path,
                "sha": result["content"]["sha"],
                "commit": result["commit"]["sha"],
                "url": result["content"]["html_url"],
            }
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def update_file(
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "",
    ) -> dict:
        """
        Update an existing file. Fetches the current SHA automatically.

        repo: repository name
        path: file path
        content: new file content as a string
        message: commit message
        branch: branch to commit to (defaults to default branch)
        """
        try:
            params = {}
            if branch:
                params["ref"] = branch
            existing = client.rest(
                "GET",
                f"/repos/{owner}/{repo}/contents/{path}",
                params=params or None,
            )
            body: dict = {
                "message": message,
                "content": base64.b64encode(content.encode()).decode(),
                "sha": existing["sha"],
            }
            if branch:
                body["branch"] = branch

            result = client.rest(
                "PUT",
                f"/repos/{owner}/{repo}/contents/{path}",
                body=body,
            )
            return {
                "success": True,
                "action": "updated",
                "path": path,
                "sha": result["content"]["sha"],
                "commit": result["commit"]["sha"],
            }
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def upsert_file(
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "",
    ) -> dict:
        """
        Create or update a file — handles both cases automatically.
        Use this when you don't know if the file exists yet.

        repo: repository name
        path: file path
        content: file content as a string
        message: commit message
        branch: branch to commit to (defaults to default branch)
        """
        try:
            params = {}
            if branch:
                params["ref"] = branch
            try:
                existing = client.rest(
                    "GET",
                    f"/repos/{owner}/{repo}/contents/{path}",
                    params=params or None,
                )
                sha = existing["sha"]
                action = "updated"
            except GitHubError:
                sha = None
                action = "created"

            body: dict = {
                "message": message,
                "content": base64.b64encode(content.encode()).decode(),
            }
            if sha:
                body["sha"] = sha
            if branch:
                body["branch"] = branch

            result = client.rest(
                "PUT",
                f"/repos/{owner}/{repo}/contents/{path}",
                body=body,
            )
            return {
                "success": True,
                "action": action,
                "path": path,
                "sha": result["content"]["sha"],
                "commit": result["commit"]["sha"],
            }
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def delete_file(
        repo: str,
        path: str,
        message: str,
        branch: str = "",
    ) -> dict:
        """
        Delete a file from a repository.

        repo: repository name
        path: file path to delete
        message: commit message
        branch: branch to commit to (defaults to default branch)
        """
        try:
            params = {}
            if branch:
                params["ref"] = branch
            existing = client.rest(
                "GET",
                f"/repos/{owner}/{repo}/contents/{path}",
                params=params or None,
            )
            body: dict = {
                "message": message,
                "sha": existing["sha"],
            }
            if branch:
                body["branch"] = branch

            client.rest(
                "DELETE",
                f"/repos/{owner}/{repo}/contents/{path}",
                body=body,
            )
            return {"success": True, "deleted": path}
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def get_file_tree(repo: str, branch: str = "", recursive: bool = True) -> list[dict]:
        """
        Get the full file tree of a repository.

        repo: repository name
        branch: branch name (defaults to default branch)
        recursive: whether to include all subdirectories (default True)
        """
        try:
            if not branch:
                repo_data = client.rest("GET", f"/repos/{owner}/{repo}")
                branch = repo_data["default_branch"]

            branch_data = client.rest(
                "GET", f"/repos/{owner}/{repo}/branches/{branch}"
            )
            tree_sha = branch_data["commit"]["commit"]["tree"]["sha"]

            params: dict = {}
            if recursive:
                params["recursive"] = "1"

            result = client.rest(
                "GET",
                f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
                params=params or None,
            )
            return [
                {
                    "path": item["path"],
                    "type": item["type"],  # "blob" or "tree"
                    "size": item.get("size"),
                    "sha": item["sha"],
                }
                for item in result.get("tree", [])
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_raw_file(repo: str, path: str, branch: str = "") -> dict:
        """
        Get raw file content without decoding — useful for binary files.
        Returns base64-encoded content.

        repo: repository name
        path: file path
        branch: branch name
        """
        try:
            params = {}
            if branch:
                params["ref"] = branch
            f = client.rest(
                "GET",
                f"/repos/{owner}/{repo}/contents/{path}",
                params=params or None,
            )
            return {
                "path": f["path"],
                "content_base64": f["content"].replace("\n", ""),
                "size": f["size"],
                "sha": f["sha"],
                "encoding": "base64",
            }
        except GitHubError as e:
            return e.to_dict()
