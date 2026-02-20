"""task command — send a prompt to a named agent and display the response."""

from __future__ import annotations

import asyncio
import json

import typer
from rich import print as rprint

from orchestration.core.agent_registry import AgentNotFoundError, get_registry
from orchestration.core.models import Message, MessageType

app = typer.Typer()

_TOOL_PREVIEW_LENGTH = 80


@app.command()
def task(
    agent_name: str = typer.Argument(help="Name of the agent to task"),
    prompt: str = typer.Argument(help="Task prompt to send"),
) -> None:
    """Send a task to a named agent and display the response."""
    asyncio.run(_task(agent_name, prompt))


async def _task(agent_name: str, prompt: str) -> None:
    try:
        registry = get_registry()
        agent = registry.get(agent_name)
        message = Message(
            sender="human",
            recipients=[agent_name],
            content=prompt,
            message_type=MessageType.chat,
        )
        messages: list[Message] = []
        async for msg in agent.handle_message(message):
            messages.append(msg)

        _display_messages(messages)
    except AgentNotFoundError:
        rprint(
            f"[red]Error: No agent named '{agent_name}'."
            " Use 'orchestration list' to see active agents.[/red]"
        )
        raise typer.Exit(code=1)


def _display_messages(messages: list[Message]) -> None:
    multi = len(messages) > 1
    for msg in messages:
        if multi:
            rprint(f"[dim]\\[{msg.sender}][/dim]", end=" ")
        # Detect tool use blocks encoded in metadata
        if msg.metadata.get("type") == "tool_use":
            tool_name = msg.metadata.get("tool_name", "tool")
            raw_input = msg.metadata.get("tool_input", {})
            preview = json.dumps(raw_input)[:_TOOL_PREVIEW_LENGTH]
            if len(json.dumps(raw_input)) > _TOOL_PREVIEW_LENGTH:
                preview += "…"
            typer.echo(f"[tool:{tool_name}] {preview}")
        else:
            typer.echo(msg.content)
