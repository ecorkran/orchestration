"""spawn command — create an agent via the daemon."""

from __future__ import annotations

import asyncio
from typing import Any

import typer
from rich import print as rprint

from orchestration.client.http import DaemonClient, DaemonNotRunningError
from orchestration.config.manager import get_config


def _resolve_spawn_model(flag: str | None) -> str | None:
    """Resolve model for spawn: CLI flag → config → None."""
    if flag is not None:
        return flag
    config_val = get_config("default_model")
    return config_val if isinstance(config_val, str) else None


def spawn(
    name: str = typer.Option(..., help="Unique agent name"),
    agent_type: str = typer.Option("sdk", "--type", help="Agent type (default: sdk)"),
    provider: str | None = typer.Option(
        None, "--provider", help="Provider name (defaults to --type)"
    ),
    cwd: str | None = typer.Option(
        None, "--cwd", help="Working directory (SDK agents)"
    ),
    system_prompt: str | None = typer.Option(
        None, "--system-prompt", help="System prompt override"
    ),
    permission_mode: str | None = typer.Option(
        None, "--permission-mode", help="SDK permission mode"
    ),
    model: str | None = typer.Option(
        None, "--model", help="Model override (e.g. opus, sonnet)"
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="Base URL for OpenAI-compatible endpoints",
    ),
) -> None:
    """Spawn a new agent."""
    resolved_provider = provider or agent_type
    resolved_model = _resolve_spawn_model(model)
    request_data: dict[str, Any] = {
        "name": name,
        "agent_type": agent_type,
        "provider": resolved_provider,
        "model": resolved_model,
        "instructions": system_prompt,
        "base_url": base_url,
        "cwd": cwd,
    }
    asyncio.run(_spawn(request_data))


async def _spawn(request_data: dict[str, Any]) -> None:
    client = DaemonClient()
    try:
        result = await client.spawn(request_data)
        rprint(
            f"[green]Agent '{result['name']}' spawned"
            f" (type: {result['agent_type']},"
            f" provider: {result['provider']})[/green]"
        )
    except DaemonNotRunningError:
        rprint(
            "[red]Error: Daemon is not running."
            " Start it with: orchestration serve[/red]"
        )
        raise typer.Exit(code=1)
    except Exception as exc:
        rprint(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)
    finally:
        await client.close()
