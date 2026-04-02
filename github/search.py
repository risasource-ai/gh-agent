"""
github/search.py

Search: code, repositories, issues, PRs, commits, users.
GitHub's search API has its own rate limit (10 req/min unauthenticated,
30 req/min authenticated) — separate from the main API.
"""

from .client import GitHubClient, GitHubError


def register(mcp, client: GitHubClient, owner: str):

    @mcp.tool()
    def search_code(
        query: str,
        repo: str = "",
        language: str = "",
        path: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """
        Search for code across GitHub repositories.

        query: search terms (e.g. "def authenticate")
        repo: limit to a specific repo (e.g. "my-repo")
        language: filter by programming language (e.g. "python")
        path: filter by file path (e.g. "src/")
        limit: max results

        Note: GitHub search has a separate rate limit of 30 req/min.
        """
        try:
            q = query
            if repo:
                q += f" repo:{owner}/{repo}"
            if language:
                q += f" language:{language}"
            if path:
                q += f" path:{path}"

            result = client.rest(
                "GET",
                "/search/code",
                params={"q": q, "per_page": min(limit, 100)},
            )
            return [
                {
                    "name": item["name"],
                    "path": item["path"],
                    "repo": item["repository"]["full_name"],
                    "url": item["html_url"],
                    "sha": item["sha"],
                }
                for item in result.get("items", [])[:limit]
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def search_repos(
        query: str,
        language: str = "",
        sort: str = "stars",
        order: str = "desc",
        limit: int = 20,
    ) -> list[dict]:
        """
        Search for repositories on GitHub.

        query: search terms (e.g. "machine learning")
        language: filter by language (e.g. "python")
        sort: "stars" | "forks" | "updated"
        order: "asc" | "desc"
        limit: max results
        """
        try:
            q = query
            if language:
                q += f" language:{language}"

            result = client.rest(
                "GET",
                "/search/repositories",
                params={"q": q, "sort": sort, "order": order, "per_page": min(limit, 100)},
            )
            return [
                {
                    "full_name": item["full_name"],
                    "description": item.get("description", ""),
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language"),
                    "url": item["html_url"],
                    "updated_at": item.get("updated_at"),
                }
                for item in result.get("items", [])[:limit]
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def search_issues(
        query: str,
        repo: str = "",
        state: str = "",
        label: str = "",
        type: str = "issue",
        sort: str = "created",
        order: str = "desc",
        limit: int = 20,
    ) -> list[dict]:
        """
        Search for issues and pull requests.

        query: search terms
        repo: limit to a specific repo (e.g. "my-repo")
        state: "open" | "closed"
        label: filter by label name
        type: "issue" | "pr"
        sort: "created" | "updated" | "comments"
        order: "asc" | "desc"
        limit: max results
        """
        try:
            q = query
            if repo:
                q += f" repo:{owner}/{repo}"
            if state:
                q += f" state:{state}"
            if label:
                q += f" label:{label}"
            if type == "pr":
                q += " is:pr"
            else:
                q += " is:issue"

            result = client.rest(
                "GET",
                "/search/issues",
                params={"q": q, "sort": sort, "order": order, "per_page": min(limit, 100)},
            )
            return [
                {
                    "number": item["number"],
                    "title": item["title"],
                    "state": item["state"],
                    "user": item["user"]["login"],
                    "repo": item["repository_url"].split("/repos/")[-1] if "repository_url" in item else "",
                    "url": item["html_url"],
                    "created_at": item.get("created_at"),
                    "labels": [l["name"] for l in item.get("labels", [])],
                }
                for item in result.get("items", [])[:limit]
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def search_commits(
        query: str,
        repo: str = "",
        author: str = "",
        since: str = "",
        until: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """
        Search for commits across GitHub.

        query: search terms (keywords that appear in commit messages)
        repo: limit to a specific repo (e.g. "my-repo")
        author: filter by commit author login
        since: ISO 8601 date — commits after this date
        until: ISO 8601 date — commits before this date
        limit: max results
        """
        try:
            q = query
            if repo:
                q += f" repo:{owner}/{repo}"
            if author:
                q += f" author:{author}"
            if since:
                q += f" committer-date:>={since}"
            if until:
                q += f" committer-date:<={until}"

            result = client.rest(
                "GET",
                "/search/commits",
                params={"q": q, "per_page": min(limit, 100)},
            )
            return [
                {
                    "sha": item["sha"][:7],
                    "message": item["commit"]["message"].split("\n")[0],
                    "author": item["commit"]["author"]["name"],
                    "date": item["commit"]["author"]["date"],
                    "repo": item["repository"]["full_name"],
                    "url": item["html_url"],
                }
                for item in result.get("items", [])[:limit]
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def search_users(
        query: str,
        type: str = "user",
        sort: str = "followers",
        limit: int = 20,
    ) -> list[dict]:
        """
        Search for GitHub users or organizations.

        query: search terms (username, name, location, etc.)
        type: "user" | "org"
        sort: "followers" | "repositories" | "joined"
        limit: max results
        """
        try:
            q = query
            if type:
                q += f" type:{type}"

            result = client.rest(
                "GET",
                "/search/users",
                params={"q": q, "sort": sort, "per_page": min(limit, 100)},
            )
            return [
                {
                    "login": item["login"],
                    "type": item.get("type", ""),
                    "url": item["html_url"],
                    "avatar_url": item.get("avatar_url", ""),
                }
                for item in result.get("items", [])[:limit]
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def search_my_code(query: str, language: str = "", limit: int = 20) -> list[dict]:
        """
        Search for code specifically within the authenticated account's repositories.
        Shorthand for search_code with user scoped to this account.

        query: search terms
        language: filter by language
        limit: max results
        """
        try:
            q = f"{query} user:{owner}"
            if language:
                q += f" language:{language}"

            result = client.rest(
                "GET",
                "/search/code",
                params={"q": q, "per_page": min(limit, 100)},
            )
            return [
                {
                    "name": item["name"],
                    "path": item["path"],
                    "repo": item["repository"]["name"],
                    "url": item["html_url"],
                    "sha": item["sha"],
                }
                for item in result.get("items", [])[:limit]
            ]
        except GitHubError as e:
            return [e.to_dict()]
