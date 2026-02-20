"""shutdown command — gracefully stop one or all agents."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint

from orchestration.core.agent_registry import AgentNotFoundError, get_registry
from orchestration.core.models import ShutdownReport


def shutdown(
    agent_name: str | None = typer.Argument(default=None, help="Agent to shut down"),
    all_agents: bool = typer.Option(False, "--all", help="Shut down all agents"),
) -> None:
    """Shut down one agent or all agents."""
    if agent_name is None and not all_agents:
        rprint("[red]Error: Provide an agent name or use --all.[/red]")
        raise typer.Exit(code=1)
    if agent_name is not None and all_agents:
        rprint("[red]Error: Provide either an agent name or --all, not both.[/red]")
        raise typer.Exit(code=1)

    if all_agents:
        asyncio.run(_shutdown_all())
    else:
        asyncio.run(_shutdown_one(agent_name))  # type: ignore[arg-type]


async def _shutdown_one(name: str) -> None:
    try:
        registry = get_registry()
        await registry.shutdown_agent(name)
        rprint(f"[green]Agent '{name}' shut down.[/green]")
    except AgentNotFoundError:
        rprint(
            f"[red]Error: No agent named '{name}'."
            " Use 'orchestration list' to see active agents.[/red]"
        )
        raise typer.Exit(code=1)


async def _shutdown_all() -> None:
    registry = get_registry()
    report: ShutdownReport = await registry.shutdown_all()
    total = len(report.succeeded) + len(report.failed)
    rprint(
        f"Shut down {total} agents."
        f" {len(report.succeeded)} succeeded, {len(report.failed)} failed."
    )
    for name, error in report.failed.items():
        rprint(f"  [red]✗ {name}: {error}[/red]")
