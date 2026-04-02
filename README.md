# gh-mcp

Full GitHub control as an MCP server.

See **[docs/README.md](docs/README.md)** for full documentation.

## Quick start

```bash
pip install uv && uv sync
cp .env.example .env
# add GITHUB_TOKEN to .env
mcp dev server.py
```

## What's included

| Module | Tools |
|---|---|
| identity | `whoami`, `get_rate_limit` |
| repos | `list_repos`, `get_repo`, `create_repo`, `update_repo`, `delete_repo`, `fork_repo`, `get_topics`, `set_topics`, `list_branches`, `get_branch`, `create_branch`, `delete_branch`, `rename_branch`, `list_commits`, `get_commit`, `list_tags`, `create_tag` |
| files | `list_files`, `read_file`, `create_file`, `update_file`, `upsert_file`, `delete_file`, `get_file_tree`, `get_raw_file` |
| pulls | `list_pulls`, `get_pull`, `create_pull`, `update_pull`, `merge_pull`, `list_pull_files`, `get_pull_diff`, `list_reviews`, `create_review`, `request_reviewers`, `list_pull_comments`, `add_pull_comment`, `reply_to_review_comment` |
| issues | `list_issues`, `get_issue`, `create_issue`, `update_issue`, `close_issue`, `list_issue_comments`, `add_issue_comment`, `update_issue_comment`, `delete_issue_comment`, `list_labels`, `create_label`, `add_labels_to_issue`, `remove_label_from_issue`, `list_milestones`, `create_milestone` |
| actions | `list_workflows`, `get_workflow`, `trigger_workflow`, `enable_workflow`, `disable_workflow`, `list_workflow_runs`, `get_workflow_run`, `cancel_workflow_run`, `rerun_workflow`, `delete_workflow_run`, `list_run_jobs`, `get_job`, `get_job_logs`, `list_repo_secrets`, `delete_repo_secret`, `list_run_artifacts`, `delete_artifact`, `list_runners` |
| releases | `list_releases`, `get_release`, `get_latest_release`, `get_release_by_tag`, `create_release`, `update_release`, `publish_release`, `delete_release`, `list_release_assets`, `delete_release_asset` |
| search | `search_code`, `search_my_code`, `search_repos`, `search_issues`, `search_commits`, `search_users` |

**164 tests, all passing.**
