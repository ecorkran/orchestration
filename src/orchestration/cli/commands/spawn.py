"""spawn command — create an agent via the registry."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint

from orchestration.config.manager import get_config
from orchestration.core.agent_registry import (
    AgentAlreadyExistsError,
    get_registry,
)
from orchestration.core.models import AgentConfig
from orchestration.providers.errors import ProviderAuthError, ProviderError


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
) -> None:
    """Spawn a new agent."""
    resolved_provider = provider or agent_type
    resolved_model = _resolve_spawn_model(model)
    config = AgentConfig(
        name=name,
        agent_type=agent_type,
        provider=resolved_provider,
        cwd=cwd,
        instructions=system_prompt,
        permission_mode=permission_mode,
        model=resolved_model,
    )
    asyncio.run(_spawn(config))


async def _spawn(config: AgentConfig) -> None:
    try:
        registry = get_registry()
        await registry.spawn(config)
        rprint(
            f"[green]Agent '{config.name}' spawned"
            f" (type: {config.agent_type}, provider: {config.provider})[/green]"
        )
    except AgentAlreadyExistsError:
        rprint(
            f"[red]Error: Agent '{config.name}' already exists."
            " Choose a different name or shut it down first.[/red]"
        )
        raise typer.Exit(code=1)
    except ProviderAuthError as exc:
        rprint(
            f"[red]Error: Authentication failed for provider"
            f" '{config.provider}'. Check your credentials. ({exc})[/red]"
        )
        raise typer.Exit(code=1)
    except ProviderError as exc:
        rprint(f"[red]Error: Provider failed — {exc}[/red]")
        raise typer.Exit(code=1)
    except KeyError:
        from orchestration.providers.registry import list_providers

        available = list_providers()
        rprint(
            f"[red]Error: Unknown provider '{config.provider}'."
            f" Available: {available}[/red]"
        )
        raise typer.Exit(code=1)
