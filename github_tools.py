"""
github_tools.py

Standalone GitHub toolkit. Give it a token, get full account control.
Import this anywhere — it has no dependency on any model or agent system.

Usage:
    from github_tools import GitHubTools
    gh = GitHubTools(token="your_pat")
    gh.list_repos()
"""

from github import Github, GithubException
from typing import Optional


class GitHubTools:
    def __init__(self, token: str):
        self._client = Github(token)
        self._user = self._client.get_user()

    # ── identity ────────────────────────────────────────────────────

    def whoami(self) -> dict:
        """Who owns this token."""
        return {
            "login": self._user.login,
            "name": self._user.name,
            "email": self._user.email,
            "public_repos": self._user.public_repos,
            "url": self._user.html_url,
        }

    # ── repos ────────────────────────────────────────────────────────

    def list_repos(self) -> list[dict]:
        """List all repos this account owns."""
        repos = []
        for r in self._user.get_repos():
            repos.append({
                "name": r.name,
                "description": r.description or "",
                "private": r.private,
                "url": r.html_url,
                "default_branch": r.default_branch,
                "updated_at": str(r.updated_at),
            })
        return repos

    def get_repo_info(self, repo_name: str) -> dict:
        """Get details about a specific repo."""
        try:
            r = self._user.get_repo(repo_name)
            return {
                "name": r.name,
                "description": r.description or "",
                "private": r.private,
                "url": r.html_url,
                "default_branch": r.default_branch,
                "stars": r.stargazers_count,
                "language": r.language,
                "topics": r.get_topics(),
                "updated_at": str(r.updated_at),
            }
        except GithubException as e:
            return {"error": str(e)}

    def create_repo(self, name: str, description: str = "",
                    private: bool = False, auto_init: bool = True) -> dict:
        """Create a new repo."""
        try:
            r = self._user.create_repo(
                name,
                description=description,
                private=private,
                auto_init=auto_init,
            )
            return {"success": True, "name": r.name, "url": r.html_url}
        except GithubException as e:
            if e.status == 422:
                return {"success": False, "error": f"repo '{name}' already exists"}
            return {"success": False, "error": str(e)}

    def delete_repo(self, repo_name: str) -> dict:
        """Delete a repo. Irreversible."""
        try:
            r = self._user.get_repo(repo_name)
            r.delete()
            return {"success": True, "deleted": repo_name}
        except GithubException as e:
            return {"success": False, "error": str(e)}

    # ── files ────────────────────────────────────────────────────────

    def list_files(self, repo_name: str, path: str = "") -> list[dict]:
        """List files/folders at a path in a repo."""
        try:
            r = self._user.get_repo(repo_name)
            contents = r.get_contents(path or "/")
            if not isinstance(contents, list):
                contents = [contents]
            return [
                {
                    "name": c.name,
                    "path": c.path,
                    "type": c.type,  # "file" or "dir"
                    "size": c.size,
                    "url": c.html_url,
                }
                for c in contents
            ]
        except GithubException as e:
            return [{"error": str(e)}]

    def read_file(self, repo_name: str, path: str) -> dict:
        """Read file contents from a repo."""
        try:
            r = self._user.get_repo(repo_name)
            f = r.get_contents(path)
            return {
                "path": f.path,
                "content": f.decoded_content.decode("utf-8"),
                "size": f.size,
                "sha": f.sha,
            }
        except GithubException as e:
            return {"error": str(e)}

    def create_file(self, repo_name: str, path: str,
                    content: str, message: str) -> dict:
        """Create a new file in a repo."""
        try:
            r = self._user.get_repo(repo_name)
            result = r.create_file(path, message, content)
            return {
                "success": True,
                "path": path,
                "commit": result["commit"].sha,
                "url": result["content"].html_url,
            }
        except GithubException as e:
            return {"success": False, "error": str(e)}

    def update_file(self, repo_name: str, path: str,
                    content: str, message: str) -> dict:
        """Update an existing file. Fetches current SHA automatically."""
        try:
            r = self._user.get_repo(repo_name)
            existing = r.get_contents(path)
            result = r.update_file(path, message, content, existing.sha)
            return {
                "success": True,
                "path": path,
                "commit": result["commit"].sha,
            }
        except GithubException as e:
            return {"success": False, "error": str(e)}

    def upsert_file(self, repo_name: str, path: str,
                    content: str, message: str) -> dict:
        """Create or update a file — don't worry about which."""
        try:
            r = self._user.get_repo(repo_name)
            try:
                existing = r.get_contents(path)
                result = r.update_file(path, message, content, existing.sha)
                return {"success": True, "action": "updated", "path": path,
                        "commit": result["commit"].sha}
            except GithubException:
                result = r.create_file(path, message, content)
                return {"success": True, "action": "created", "path": path,
                        "commit": result["commit"].sha}
        except GithubException as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, repo_name: str, path: str, message: str) -> dict:
        """Delete a file from a repo."""
        try:
            r = self._user.get_repo(repo_name)
            f = r.get_contents(path)
            r.delete_file(path, message, f.sha)
            return {"success": True, "deleted": path}
        except GithubException as e:
            return {"success": False, "error": str(e)}

    # ── branches ─────────────────────────────────────────────────────

    def list_branches(self, repo_name: str) -> list[dict]:
        """List all branches in a repo."""
        try:
            r = self._user.get_repo(repo_name)
            return [{"name": b.name, "sha": b.commit.sha} for b in r.get_branches()]
        except GithubException as e:
            return [{"error": str(e)}]

    def create_branch(self, repo_name: str, branch_name: str,
                      from_branch: Optional[str] = None) -> dict:
        """Create a new branch."""
        try:
            r = self._user.get_repo(repo_name)
            source = from_branch or r.default_branch
            sha = r.get_branch(source).commit.sha
            r.create_git_ref(f"refs/heads/{branch_name}", sha)
            return {"success": True, "branch": branch_name, "from": source}
        except GithubException as e:
            return {"success": False, "error": str(e)}

    # ── commits ──────────────────────────────────────────────────────

    def list_commits(self, repo_name: str, limit: int = 10) -> list[dict]:
        """Recent commits on default branch."""
        try:
            r = self._user.get_repo(repo_name)
            commits = []
            for c in r.get_commits()[:limit]:
                commits.append({
                    "sha": c.sha[:7],
                    "message": c.commit.message.split("\n")[0],
                    "author": c.commit.author.name,
                    "date": str(c.commit.author.date),
                })
            return commits
        except GithubException as e:
            return [{"error": str(e)}]

    # ── tool definitions for model ────────────────────────────────────

    @staticmethod
    def tool_definitions() -> list[dict]:
        """
        Returns tool definitions in Anthropic format.
        Pass this to the model so it knows what tools exist.
        """
        return [
            {
                "name": "whoami",
                "description": "Get info about the GitHub account you own",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "list_repos",
                "description": "List all repos in the account",
                "input_schema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "get_repo_info",
                "description": "Get details about a specific repo",
                "input_schema": {
                    "type": "object",
                    "properties": {"repo_name": {"type": "string"}},
                    "required": ["repo_name"],
                },
            },
            {
                "name": "create_repo",
                "description": "Create a new GitHub repo",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "repo name"},
                        "description": {"type": "string"},
                        "private": {"type": "boolean", "default": False},
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "delete_repo",
                "description": "Permanently delete a repo",
                "input_schema": {
                    "type": "object",
                    "properties": {"repo_name": {"type": "string"}},
                    "required": ["repo_name"],
                },
            },
            {
                "name": "list_files",
                "description": "List files and folders at a path in a repo",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "path": {"type": "string", "default": ""},
                    },
                    "required": ["repo_name"],
                },
            },
            {
                "name": "read_file",
                "description": "Read the contents of a file in a repo",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "path": {"type": "string"},
                    },
                    "required": ["repo_name", "path"],
                },
            },
            {
                "name": "create_file",
                "description": "Create a new file in a repo",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "message": {"type": "string", "description": "commit message"},
                    },
                    "required": ["repo_name", "path", "content", "message"],
                },
            },
            {
                "name": "update_file",
                "description": "Update an existing file in a repo",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "message": {"type": "string"},
                    },
                    "required": ["repo_name", "path", "content", "message"],
                },
            },
            {
                "name": "upsert_file",
                "description": "Create or update a file — handles both cases automatically",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "message": {"type": "string"},
                    },
                    "required": ["repo_name", "path", "content", "message"],
                },
            },
            {
                "name": "delete_file",
                "description": "Delete a file from a repo",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "path": {"type": "string"},
                        "message": {"type": "string"},
                    },
                    "required": ["repo_name", "path", "message"],
                },
            },
            {
                "name": "list_branches",
                "description": "List all branches in a repo",
                "input_schema": {
                    "type": "object",
                    "properties": {"repo_name": {"type": "string"}},
                    "required": ["repo_name"],
                },
            },
            {
                "name": "create_branch",
                "description": "Create a new branch in a repo",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "branch_name": {"type": "string"},
                        "from_branch": {"type": "string", "description": "source branch, defaults to main"},
                    },
                    "required": ["repo_name", "branch_name"],
                },
            },
            {
                "name": "list_commits",
                "description": "List recent commits on the default branch",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["repo_name"],
                },
            },
        ]

    def execute_tool(self, name: str, inputs: dict):
        """
        Execute a tool by name. Called by the agent loop.
        Returns whatever the tool returns.
        """
        tools = {
            "whoami": lambda: self.whoami(),
            "list_repos": lambda: self.list_repos(),
            "get_repo_info": lambda: self.get_repo_info(**inputs),
            "create_repo": lambda: self.create_repo(**inputs),
            "delete_repo": lambda: self.delete_repo(**inputs),
            "list_files": lambda: self.list_files(**inputs),
            "read_file": lambda: self.read_file(**inputs),
            "create_file": lambda: self.create_file(**inputs),
            "update_file": lambda: self.update_file(**inputs),
            "upsert_file": lambda: self.upsert_file(**inputs),
            "delete_file": lambda: self.delete_file(**inputs),
            "list_branches": lambda: self.list_branches(**inputs),
            "create_branch": lambda: self.create_branch(**inputs),
            "list_commits": lambda: self.list_commits(**inputs),
        }
        fn = tools.get(name)
        if not fn:
            return {"error": f"unknown tool: {name}"}
        return fn()
