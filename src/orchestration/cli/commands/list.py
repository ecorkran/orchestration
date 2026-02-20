"""list command — display active agents in a rich table."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from orchestration.core.agent_registry import get_registry
from orchestration.core.models import AgentInfo, AgentState

_STATE_COLORS: dict[str, str] = {
    AgentState.idle: "green",
    AgentState.processing: "yellow",
    AgentState.terminated: "red",
    AgentState.failed: "red",
    AgentState.restarting: "cyan",
}


def list_agents(
    state: str | None = typer.Option(None, "--state", help="Filter by agent state"),
    provider: str | None = typer.Option(None, "--provider", help="Filter by provider"),
) -> None:
    """List active agents."""
    asyncio.run(_list_agents(state, provider))


async def _list_agents(state_filter: str | None, provider_filter: str | None) -> None:
    registry = get_registry()
    agent_state = AgentState(state_filter) if state_filter else None
    agents: list[AgentInfo] = registry.list_agents(
        state=agent_state, provider=provider_filter
    )

    if not agents:
        typer.echo("No agents running.")
        return

    table = Table(title="Active Agents")
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Provider")
    table.add_column("State")

    for info in agents:
        color = _STATE_COLORS.get(info.state, "white")
        table.add_row(
            info.name,
            info.agent_type,
            info.provider,
            f"[{color}]{info.state}[/{color}]",
        )

    Console().print(table)
