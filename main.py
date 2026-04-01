"""
main.py

Entry point. Give it a task, it runs.

Usage:
    python main.py "create a repo called my-notes with a README"
    python main.py  (interactive mode)
"""

import os
import sys
from dotenv import load_dotenv
from github_tools import GitHubTools
from agent_loop import run_agent

load_dotenv()


def get_config() -> dict:
    """Read config from environment. Fails loudly if anything is missing."""
    missing = []

    github_token = os.getenv("GITHUB_TOKEN")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not github_token:
        missing.append("GITHUB_TOKEN")
    if not anthropic_key:
        missing.append("ANTHROPIC_API_KEY")

    if missing:
        print(f"\n[error] missing environment variables: {', '.join(missing)}")
        print("create a .env file with:")
        for m in missing:
            print(f"  {m}=your_value_here")
        print("\nsee .env.example for reference\n")
        sys.exit(1)

    return {
        "github_token": github_token,
        "anthropic_key": anthropic_key,
        "model": os.getenv("MODEL", "claude-opus-4-6"),
    }


def main():
    config = get_config()

    # init tools
    gh = GitHubTools(token=config["github_token"])

    # verify github connection
    try:
        me = gh.whoami()
        print(f"\nconnected as: {me['login']} ({me['public_repos']} repos)")
    except Exception as e:
        print(f"\n[error] github connection failed: {e}")
        print("check your GITHUB_TOKEN in .env\n")
        sys.exit(1)

    # get task from args or prompt
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        print("\nwhat should i do? (ctrl+c to exit)")
        task = input("> ").strip()
        if not task:
            print("no task given, exiting")
            sys.exit(0)

    # run
    result = run_agent(
        task=task,
        tools=gh,
        api_key=config["anthropic_key"],
        model=config["model"],
        verbose=True,
    )

    if result:
        print(f"\nfinal: {result}")


if __name__ == "__main__":
    main()
