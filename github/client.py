"""
github/client.py

Raw GitHub API client. Two methods: rest() and graphql().
No abstraction beyond auth and error handling — callers get dicts back.

Every module imports this. Nothing else is shared.
"""

import httpx
from typing import Any


GITHUB_API = "https://api.github.com"
GITHUB_GRAPHQL = "https://api.github.com/graphql"


class GitHubClient:
    def __init__(self, token: str):
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    # ── REST ─────────────────────────────────────────────────────────

    def rest(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        body: dict | None = None,
    ) -> dict | list:
        """
        Make a REST API call.

        path: e.g. "/repos/{owner}/{repo}/pulls"
        Returns parsed JSON or raises with a clear message.
        """
        url = f"{GITHUB_API}{path}"
        with httpx.Client(headers=self._headers) as http:
            response = http.request(
                method=method.upper(),
                url=url,
                params=params,
                json=body,
            )

        if not response.is_success:
            error = _extract_error(response)
            raise GitHubError(
                status=response.status_code,
                message=error,
                path=path,
            )

        if response.status_code == 204 or not response.content:
            return {"success": True}

        return response.json()

    def paginate(
        self,
        path: str,
        params: dict | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Fetch all pages of a REST endpoint up to limit items.
        GitHub uses Link headers for pagination.
        """
        params = {**(params or {}), "per_page": min(limit, 100), "page": 1}
        results = []

        while True:
            url = f"{GITHUB_API}{path}"
            with httpx.Client(headers=self._headers) as http:
                response = http.get(url, params=params)

            if not response.is_success:
                raise GitHubError(
                    status=response.status_code,
                    message=_extract_error(response),
                    path=path,
                )

            page = response.json()
            if not isinstance(page, list):
                return page

            results.extend(page)

            if len(results) >= limit or "next" not in response.links:
                break

            params["page"] += 1

        return results[:limit]

    # ── GraphQL ──────────────────────────────────────────────────────

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        """
        Run a GraphQL query or mutation.
        Returns the 'data' key, raises on errors.

        Used for: Projects v2, Discussions, and anything REST doesn't cover.
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        with httpx.Client(headers=self._headers) as http:
            response = http.post(GITHUB_GRAPHQL, json=payload)

        if not response.is_success:
            raise GitHubError(
                status=response.status_code,
                message=_extract_error(response),
                path="graphql",
            )

        result = response.json()

        if "errors" in result:
            messages = [e.get("message", str(e)) for e in result["errors"]]
            raise GitHubError(
                status=200,
                message="; ".join(messages),
                path="graphql",
            )

        return result.get("data", {})

    # ── identity helper ───────────────────────────────────────────────

    def whoami(self) -> dict:
        """Return the authenticated user."""
        return self.rest("GET", "/user")


# ── error type ────────────────────────────────────────────────────────

class GitHubError(Exception):
    def __init__(self, status: int, message: str, path: str):
        self.status = status
        self.message = message
        self.path = path
        super().__init__(f"GitHub {status} on {path}: {message}")

    def to_dict(self) -> dict:
        return {
            "error": True,
            "status": self.status,
            "message": self.message,
            "path": self.path,
        }


# ── internal helpers ─────────────────────────────────────────────────

def _extract_error(response: httpx.Response) -> str:
    try:
        data = response.json()
        return data.get("message", str(data))
    except Exception:
        return response.text or f"HTTP {response.status_code}"
