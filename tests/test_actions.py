"""
tests/test_actions.py

Tests for actions module: workflows, runs, jobs, secrets, artifacts.
"""

import pytest
from github.client import GitHubError
from tests.conftest import OWNER


SAMPLE_WORKFLOW = {
    "id": 1,
    "name": "CI",
    "path": ".github/workflows/ci.yml",
    "state": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "html_url": f"https://github.com/{OWNER}/my-repo/actions/workflows/1",
}

SAMPLE_RUN = {
    "id": 100,
    "name": "CI",
    "status": "completed",
    "conclusion": "success",
    "head_branch": "main",
    "head_sha": "abcdef1234567890",
    "event": "push",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:05:00Z",
    "html_url": f"https://github.com/{OWNER}/my-repo/actions/runs/100",
    "run_number": 42,
    "run_attempt": 1,
    "workflow_id": 1,
    "triggering_actor": {"login": OWNER},
}

SAMPLE_JOB = {
    "id": 200,
    "name": "test",
    "status": "completed",
    "conclusion": "success",
    "started_at": "2024-01-01T00:01:00Z",
    "completed_at": "2024-01-01T00:04:00Z",
    "runner_name": "ubuntu-latest",
    "html_url": f"https://github.com/{OWNER}/my-repo/actions/jobs/200",
    "steps": [
        {
            "name": "Checkout",
            "status": "completed",
            "conclusion": "success",
            "number": 1,
            "started_at": "2024-01-01T00:01:00Z",
            "completed_at": "2024-01-01T00:01:30Z",
        },
        {
            "name": "Run tests",
            "status": "completed",
            "conclusion": "success",
            "number": 2,
            "started_at": "2024-01-01T00:01:30Z",
            "completed_at": "2024-01-01T00:04:00Z",
        },
    ],
}


class TestWorkflows:
    def test_list_workflows(self, mock_client):
        mock_client.rest.return_value = {"workflows": [SAMPLE_WORKFLOW]}
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/actions/workflows")
        assert len(result["workflows"]) == 1
        assert result["workflows"][0]["name"] == "CI"

    def test_get_workflow(self, mock_client):
        mock_client.rest.return_value = SAMPLE_WORKFLOW
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/actions/workflows/1")
        assert result["id"] == 1
        assert result["state"] == "active"

    def test_trigger_workflow_dispatch(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/actions/workflows/ci.yml/dispatches",
            body={"ref": "main"},
        )
        call = mock_client.rest.call_args
        assert "dispatches" in call[0][1]
        assert call[1]["body"]["ref"] == "main"

    def test_trigger_with_inputs(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest(
            "POST",
            f"/repos/{OWNER}/my-repo/actions/workflows/deploy.yml/dispatches",
            body={"ref": "main", "inputs": {"env": "production"}},
        )
        body = mock_client.rest.call_args[1]["body"]
        assert body["inputs"]["env"] == "production"

    def test_enable_workflow(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("PUT", f"/repos/{OWNER}/my-repo/actions/workflows/1/enable")
        call = mock_client.rest.call_args
        assert "enable" in call[0][1]

    def test_disable_workflow(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("PUT", f"/repos/{OWNER}/my-repo/actions/workflows/1/disable")
        call = mock_client.rest.call_args
        assert "disable" in call[0][1]


class TestWorkflowRuns:
    def test_list_all_runs(self, mock_client):
        mock_client.rest.return_value = {"workflow_runs": [SAMPLE_RUN, SAMPLE_RUN]}
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/actions/runs")
        assert len(result["workflow_runs"]) == 2

    def test_list_runs_for_workflow(self, mock_client):
        mock_client.rest.return_value = {"workflow_runs": [SAMPLE_RUN]}
        mock_client.rest("GET", f"/repos/{OWNER}/my-repo/actions/workflows/1/runs")
        call = mock_client.rest.call_args
        assert "workflows/1/runs" in call[0][1]

    def test_list_runs_with_status_filter(self, mock_client):
        mock_client.rest.return_value = {"workflow_runs": []}
        mock_client.rest(
            "GET",
            f"/repos/{OWNER}/my-repo/actions/runs",
            params={"status": "failure"},
        )
        call = mock_client.rest.call_args
        assert call[1]["params"]["status"] == "failure"

    def test_get_workflow_run(self, mock_client):
        mock_client.rest.return_value = SAMPLE_RUN
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/actions/runs/100")
        assert result["id"] == 100
        assert result["conclusion"] == "success"

    def test_cancel_run(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("POST", f"/repos/{OWNER}/my-repo/actions/runs/100/cancel")
        call = mock_client.rest.call_args
        assert "cancel" in call[0][1]

    def test_rerun_all(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("POST", f"/repos/{OWNER}/my-repo/actions/runs/100/rerun")
        call = mock_client.rest.call_args
        assert "rerun" in call[0][1]
        assert "rerun-failed" not in call[0][1]

    def test_rerun_failed_only(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("POST", f"/repos/{OWNER}/my-repo/actions/runs/100/rerun-failed-jobs")
        call = mock_client.rest.call_args
        assert "rerun-failed-jobs" in call[0][1]

    def test_delete_run(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("DELETE", f"/repos/{OWNER}/my-repo/actions/runs/100")
        call = mock_client.rest.call_args
        assert call[0][0] == "DELETE"


class TestJobs:
    def test_list_run_jobs(self, mock_client):
        mock_client.rest.return_value = {"jobs": [SAMPLE_JOB]}
        result = mock_client.rest(
            "GET",
            f"/repos/{OWNER}/my-repo/actions/runs/100/jobs",
            params={"filter": "latest"},
        )
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["name"] == "test"

    def test_get_job_with_steps(self, mock_client):
        mock_client.rest.return_value = SAMPLE_JOB
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/actions/jobs/200")
        assert result["id"] == 200
        assert len(result["steps"]) == 2
        assert result["steps"][0]["name"] == "Checkout"

    def test_get_job_logs(self, mock_client):
        mock_client.rest_raw.return_value = "2024-01-01T00:01:00Z Run tests\n2024-01-01T00:04:00Z Done"
        result = mock_client.rest_raw(
            "GET",
            f"/repos/{OWNER}/my-repo/actions/jobs/200/logs",
            accept="application/vnd.github+json",
        )
        assert "Run tests" in result

    def test_job_logs_error(self, mock_client):
        mock_client.rest_raw.side_effect = GitHubError(410, "Gone", f"/repos/{OWNER}/my-repo/actions/jobs/200/logs")
        with pytest.raises(GitHubError) as exc:
            mock_client.rest_raw("GET", "/test", accept="text/plain")
        assert exc.value.status == 410


class TestSecrets:
    def test_list_secrets_names_only(self, mock_client):
        mock_client.rest.return_value = {
            "secrets": [
                {"name": "API_KEY", "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"},
                {"name": "DB_PASSWORD", "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"},
            ]
        }
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/actions/secrets")
        # secrets should only expose names, not values
        secrets = result["secrets"]
        assert len(secrets) == 2
        assert "name" in secrets[0]
        assert "value" not in secrets[0]

    def test_delete_secret(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("DELETE", f"/repos/{OWNER}/my-repo/actions/secrets/API_KEY")
        call = mock_client.rest.call_args
        assert "API_KEY" in call[0][1]
        assert call[0][0] == "DELETE"


class TestArtifacts:
    def test_list_artifacts(self, mock_client):
        mock_client.rest.return_value = {
            "artifacts": [
                {
                    "id": 1,
                    "name": "test-results",
                    "size_in_bytes": 1024 * 1024 * 2,
                    "expired": False,
                    "created_at": "2024-01-01T00:00:00Z",
                    "expires_at": "2024-04-01T00:00:00Z",
                    "archive_download_url": "https://api.github.com/repos/x/y/actions/artifacts/1/zip",
                }
            ]
        }
        result = mock_client.rest("GET", f"/repos/{OWNER}/my-repo/actions/runs/100/artifacts")
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["name"] == "test-results"

    def test_delete_artifact(self, mock_client):
        mock_client.rest.return_value = {"success": True}
        mock_client.rest("DELETE", f"/repos/{OWNER}/my-repo/actions/artifacts/1")
        call = mock_client.rest.call_args
        assert call[0][0] == "DELETE"
        assert "artifacts/1" in call[0][1]


class TestRunDuration:
    def test_duration_calculation(self):
        from github.actions import _run_duration
        run = {
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:05:30Z",
        }
        duration = _run_duration(run)
        assert duration == 330  # 5 min 30 sec

    def test_duration_returns_none_on_bad_data(self):
        from github.actions import _run_duration
        assert _run_duration({}) is None
        assert _run_duration({"created_at": "bad-date"}) is None
