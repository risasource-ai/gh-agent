"""
agent_loop.py

Generic tool-calling loop. Give it a model, tools, and a task.
It runs until the model says it's done.

Not GitHub-specific — plug in any tools and it works the same way.

Usage:
    from agent_loop import run_agent
    result = run_agent(task="create a repo called test", tools=gh_tools)
"""

import json
import anthropic


SYSTEM_PROMPT = """You are an autonomous agent with full control over a GitHub account.
You own this account completely — you can read everything, create anything, modify anything.

Work through tasks step by step:
1. First understand what exists (list repos, read files) before acting
2. Plan your actions before executing them
3. Execute one step at a time
4. Verify your work when done

Be thorough. When you finish a task, summarize exactly what you did."""


def run_agent(
    task: str,
    tools,                    # GitHubTools instance (or anything with tool_definitions + execute_tool)
    api_key: str,
    model: str = "claude-opus-4-6",
    max_iterations: int = 30,
    verbose: bool = True,
) -> str:
    """
    Run the agent loop until the task is complete.

    Args:
        task:           What you want the agent to do
        tools:          Tool provider (has tool_definitions() and execute_tool())
        api_key:        Anthropic API key
        model:          Which Claude model to use
        max_iterations: Safety limit on tool call rounds
        verbose:        Print each step as it happens

    Returns:
        Final response text from the model
    """

    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": task}]
    tool_defs = tools.tool_definitions()

    if verbose:
        print(f"\n{'='*60}")
        print(f"TASK: {task}")
        print(f"{'='*60}\n")

    for iteration in range(max_iterations):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tool_defs,
            messages=messages,
        )

        # collect text and tool calls from response
        text_parts = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        # print any model text
        if verbose and text_parts:
            for text in text_parts:
                if text.strip():
                    print(f"[model] {text.strip()}\n")

        # if no tool calls, model is done
        if response.stop_reason == "end_turn" or not tool_calls:
            final_text = "\n".join(text_parts)
            if verbose:
                print(f"\n{'='*60}")
                print("DONE")
                print(f"{'='*60}\n")
            return final_text

        # add model response to conversation
        messages.append({"role": "assistant", "content": response.content})

        # execute each tool call and collect results
        tool_results = []
        for tool_call in tool_calls:
            name = tool_call.name
            inputs = tool_call.input

            if verbose:
                inputs_display = json.dumps(inputs, indent=2) if inputs else "{}"
                print(f"[tool] {name}({inputs_display})")

            result = tools.execute_tool(name, inputs)

            if verbose:
                result_str = json.dumps(result, indent=2, default=str)
                # trim long results for display
                if len(result_str) > 500:
                    result_str = result_str[:500] + "\n... (truncated)"
                print(f"[result] {result_str}\n")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call.id,
                "content": json.dumps(result, default=str),
            })

        # add tool results to conversation
        messages.append({"role": "user", "content": tool_results})

    return f"reached max iterations ({max_iterations}) — task may be incomplete"
