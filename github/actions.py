"""
github/actions.py

GitHub Actions: workflows, runs, jobs, logs, secrets, artifacts.
This is the missing piece for autonomous work — without it the agent
can push code but can't verify if it actually works.
"""

from .client import GitHubClient, GitHubError


def register(mcp, client: GitHubClient, owner: str):

    # ── workflows ────────────────────────────────────────────────────

    @mcp.tool()
    def list_workflows(repo: str) -> list[dict]:
        """
        List all workflows in a repository.

        repo: repository name
        """
        try:
            result = client.rest("GET", f"/repos/{owner}/{repo}/actions/workflows")
            return [_shape_workflow(w) for w in result.get("workflows", [])]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_workflow(repo: str, workflow_id: str) -> dict:
        """
        Get details of a specific workflow.

        repo: repository name
        workflow_id: workflow ID (number) or filename (e.g. "ci.yml")
        """
        try:
            result = client.rest(
                "GET", f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}"
            )
            return _shape_workflow(result)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def trigger_workflow(
        repo: str,
        workflow_id: str,
        ref: str = "main",
        inputs: dict | None = None,
    ) -> dict:
        """
        Trigger a workflow run (workflow_dispatch event).

        repo: repository name
        workflow_id: workflow ID or filename (e.g. "ci.yml")
        ref: branch or tag to run on (default "main")
        inputs: optional workflow inputs as key-value pairs
        """
        try:
            body: dict = {"ref": ref}
            if inputs:
                body["inputs"] = inputs
            client.rest(
                "POST",
                f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
                body=body,
            )
            return {"success": True, "workflow_id": workflow_id, "ref": ref}
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def enable_workflow(repo: str, workflow_id: str) -> dict:
        """Enable a disabled workflow."""
        try:
            client.rest(
                "PUT",
                f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/enable",
            )
            return {"success": True, "workflow_id": workflow_id, "state": "enabled"}
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def disable_workflow(repo: str, workflow_id: str) -> dict:
        """Disable a workflow from running."""
        try:
            client.rest(
                "PUT",
                f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/disable",
            )
            return {"success": True, "workflow_id": workflow_id, "state": "disabled"}
        except GitHubError as e:
            return e.to_dict()

    # ── workflow runs ─────────────────────────────────────────────────

    @mcp.tool()
    def list_workflow_runs(
        repo: str,
        workflow_id: str = "",
        branch: str = "",
        status: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """
        List workflow runs for a repo or specific workflow.

        repo: repository name
        workflow_id: filter by workflow ID or filename (optional)
        branch: filter by branch name
        status: "queued" | "in_progress" | "completed" | "success" |
                "failure" | "cancelled" | "skipped" | "waiting"
        limit: max runs to return
        """
        try:
            if workflow_id:
                path = f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
            else:
                path = f"/repos/{owner}/{repo}/actions/runs"

            params: dict = {}
            if branch:
                params["branch"] = branch
            if status:
                params["status"] = status

            result = client.rest("GET", path, params=params or None)
            runs = result.get("workflow_runs", [])[:limit]
            return [_shape_run(r) for r in runs]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_workflow_run(repo: str, run_id: int) -> dict:
        """
        Get details of a specific workflow run.

        repo: repository name
        run_id: run ID number
        """
        try:
            r = client.rest("GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}")
            return _shape_run(r, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def cancel_workflow_run(repo: str, run_id: int) -> dict:
        """
        Cancel a workflow run that is queued or in progress.

        repo: repository name
        run_id: run ID number
        """
        try:
            client.rest(
                "POST", f"/repos/{owner}/{repo}/actions/runs/{run_id}/cancel"
            )
            return {"success": True, "run_id": run_id, "action": "cancelled"}
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def rerun_workflow(repo: str, run_id: int, failed_only: bool = False) -> dict:
        """
        Re-run a workflow run.

        repo: repository name
        run_id: run ID number
        failed_only: if True, only re-run failed jobs
        """
        try:
            if failed_only:
                path = f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs"
            else:
                path = f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun"
            client.rest("POST", path)
            return {"success": True, "run_id": run_id, "failed_only": failed_only}
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def delete_workflow_run(repo: str, run_id: int) -> dict:
        """
        Delete a workflow run from history.

        repo: repository name
        run_id: run ID number
        """
        try:
            client.rest("DELETE", f"/repos/{owner}/{repo}/actions/runs/{run_id}")
            return {"success": True, "deleted_run": run_id}
        except GitHubError as e:
            return e.to_dict()

    # ── jobs ─────────────────────────────────────────────────────────

    @mcp.tool()
    def list_run_jobs(repo: str, run_id: int, filter: str = "latest") -> list[dict]:
        """
        List jobs in a workflow run.

        repo: repository name
        run_id: run ID number
        filter: "latest" | "all" — whether to return latest or all attempts
        """
        try:
            result = client.rest(
                "GET",
                f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs",
                params={"filter": filter},
            )
            return [_shape_job(j) for j in result.get("jobs", [])]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def get_job(repo: str, job_id: int) -> dict:
        """
        Get details of a specific job, including step results.

        repo: repository name
        job_id: job ID number
        """
        try:
            j = client.rest("GET", f"/repos/{owner}/{repo}/actions/jobs/{job_id}")
            return _shape_job(j, full=True)
        except GitHubError as e:
            return e.to_dict()

    @mcp.tool()
    def get_job_logs(repo: str, job_id: int) -> dict:
        """
        Get the log output of a specific job.
        Logs are returned as plain text.

        repo: repository name
        job_id: job ID number
        """
        try:
            logs = client.rest_raw(
                "GET",
                f"/repos/{owner}/{repo}/actions/jobs/{job_id}/logs",
                accept="application/vnd.github+json",
            )
            return {"job_id": job_id, "logs": logs}
        except GitHubError as e:
            return e.to_dict()

    # ── secrets ───────────────────────────────────────────────────────

    @mcp.tool()
    def list_repo_secrets(repo: str) -> list[dict]:
        """
        List secret names in a repository.
        Values are never returned — names only.

        repo: repository name
        """
        try:
            result = client.rest(
                "GET", f"/repos/{owner}/{repo}/actions/secrets"
            )
            return [
                {
                    "name": s["name"],
                    "created_at": s.get("created_at"),
                    "updated_at": s.get("updated_at"),
                }
                for s in result.get("secrets", [])
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def delete_repo_secret(repo: str, secret_name: str) -> dict:
        """
        Delete a secret from a repository.

        repo: repository name
        secret_name: name of the secret to delete
        """
        try:
            client.rest(
                "DELETE",
                f"/repos/{owner}/{repo}/actions/secrets/{secret_name}",
            )
            return {"success": True, "deleted_secret": secret_name}
        except GitHubError as e:
            return e.to_dict()

    # ── artifacts ─────────────────────────────────────────────────────

    @mcp.tool()
    def list_run_artifacts(repo: str, run_id: int) -> list[dict]:
        """
        List artifacts produced by a workflow run.

        repo: repository name
        run_id: run ID number
        """
        try:
            result = client.rest(
                "GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
            )
            return [
                {
                    "id": a["id"],
                    "name": a["name"],
                    "size_mb": round(a["size_in_bytes"] / 1024 / 1024, 2),
                    "expired": a.get("expired", False),
                    "created_at": a.get("created_at"),
                    "expires_at": a.get("expires_at"),
                    "url": a.get("archive_download_url"),
                }
                for a in result.get("artifacts", [])
            ]
        except GitHubError as e:
            return [e.to_dict()]

    @mcp.tool()
    def delete_artifact(repo: str, artifact_id: int) -> dict:
        """
        Delete a workflow artifact.

        repo: repository name
        artifact_id: artifact ID number
        """
        try:
            client.rest(
                "DELETE",
                f"/repos/{owner}/{repo}/actions/artifacts/{artifact_id}",
            )
            return {"success": True, "deleted_artifact": artifact_id}
        except GitHubError as e:
            return e.to_dict()

    # ── runners ───────────────────────────────────────────────────────

    @mcp.tool()
    def list_runners(repo: str) -> list[dict]:
        """
        List self-hosted runners for a repository.

        repo: repository name
        """
        try:
            result = client.rest(
                "GET", f"/repos/{owner}/{repo}/actions/runners"
            )
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "os": r.get("os"),
                    "status": r.get("status"),
                    "busy": r.get("busy", False),
                    "labels": [l["name"] for l in r.get("labels", [])],
                }
                for r in result.get("runners", [])
            ]
        except GitHubError as e:
            return [e.to_dict()]


# ── shape helpers ─────────────────────────────────────────────────────

def _shape_workflow(w: dict) -> dict:
    return {
        "id": w["id"],
        "name": w["name"],
        "path": w.get("path", ""),
        "state": w.get("state", ""),
        "created_at": w.get("created_at"),
        "updated_at": w.get("updated_at"),
        "url": w.get("html_url"),
    }


def _shape_run(r: dict, full: bool = False) -> dict:
    base = {
        "id": r["id"],
        "name": r.get("name", ""),
        "status": r.get("status", ""),
        "conclusion": r.get("conclusion"),
        "branch": r.get("head_branch", ""),
        "sha": r.get("head_sha", "")[:7] if r.get("head_sha") else "",
        "event": r.get("event", ""),
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
        "url": r.get("html_url"),
        "run_number": r.get("run_number"),
    }
    if full:
        base.update({
            "run_attempt": r.get("run_attempt", 1),
            "workflow_id": r.get("workflow_id"),
            "triggering_actor": r["triggering_actor"]["login"] if r.get("triggering_actor") else None,
            "duration_seconds": _run_duration(r),
        })
    return base


def _shape_job(j: dict, full: bool = False) -> dict:
    base = {
        "id": j["id"],
        "name": j["name"],
        "status": j.get("status", ""),
        "conclusion": j.get("conclusion"),
        "started_at": j.get("started_at"),
        "completed_at": j.get("completed_at"),
        "runner_name": j.get("runner_name"),
        "url": j.get("html_url"),
    }
    if full:
        base["steps"] = [
            {
                "name": s["name"],
                "status": s.get("status"),
                "conclusion": s.get("conclusion"),
                "number": s.get("number"),
                "started_at": s.get("started_at"),
                "completed_at": s.get("completed_at"),
            }
            for s in j.get("steps", [])
        ]
    return base


def _run_duration(r: dict) -> int | None:
    """Return run duration in seconds, or None if not complete."""
    try:
        from datetime import datetime
        start = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00"))
        return int((end - start).total_seconds())
    except Exception:
        return None
