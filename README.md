# gh-agent

A model that owns a GitHub account. Give it a task, it figures out the steps.

## What it is

Three files, each independently useful:

```
github_tools.py   ← full GitHub control, no model dependency
agent_loop.py     ← generic tool-calling loop, not GitHub-specific  
main.py           ← entry point, reads .env, runs
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env with your keys
```

**.env:**
```
GITHUB_TOKEN=your_pat_here
ANTHROPIC_API_KEY=your_key_here
```

**GitHub PAT scopes needed:** `repo` (+ `delete_repo` if you want deletion)
Create at: github.com → Settings → Developer settings → Personal access tokens

## Usage

```bash
# give it a task directly
python main.py "create a repo called my-project with a proper README and a .gitignore for Python"

# or interactive mode
python main.py
> what should i do?
```

## What the model can do

- List, create, delete repos
- Read any file in any repo
- Create, update, delete files
- Create branches
- See commit history
- Understand what already exists before acting

## How it works

```
your task
    ↓
model sees task + available tools
    ↓
model calls tools (list repos, read files, etc.)
    ↓
your machine executes the calls with your token
    ↓
results go back to model
    ↓
model calls more tools or says done
```

Token never leaves your machine. Model only sees tool results.

## Using just the GitHub tools (no model)

```python
from github_tools import GitHubTools

gh = GitHubTools(token="your_pat")
gh.list_repos()
gh.create_repo("my-repo", description="test")
gh.upsert_file("my-repo", "README.md", "# hello", "initial commit")
gh.read_file("my-repo", "README.md")
```

## Using a different model

```python
from github_tools import GitHubTools
from agent_loop import run_agent

gh = GitHubTools(token="your_pat")
result = run_agent(
    task="your task here",
    tools=gh,
    api_key="your_anthropic_key",
    model="claude-sonnet-4-6",  # or any claude model
)
```

## Adding more tools later

`agent_loop.py` is not GitHub-specific. Any object with `tool_definitions()` and `execute_tool()` methods works. Later you can add filesystem tools, browser tools, etc. and pass them in the same way.
