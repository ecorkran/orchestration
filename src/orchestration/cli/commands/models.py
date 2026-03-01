"""models command — list available models from an OpenAI-compatible endpoint."""

from __future__ import annotations

import asyncio

import httpx
import typer
from rich import print as rprint

from orchestration.providers.profiles import get_profile


def models(
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Provider profile to resolve base URL from (e.g. openrouter, local)",
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="Base URL of an OpenAI-compatible endpoint",
    ),
) -> None:
    """List models available from an OpenAI-compatible endpoint."""
    if profile is None and base_url is None:
        rprint("[red]Error: provide --profile or --base-url[/red]")
        raise typer.Exit(code=1)

    resolved_url = base_url
    if resolved_url is None:
        try:
            p = get_profile(profile)  # type: ignore[arg-type]
            resolved_url = p.base_url
        except KeyError as exc:
            rprint(f"[red]Error: {exc}[/red]")
            raise typer.Exit(code=1)

    if resolved_url is None:
        rprint("[red]Error: profile has no base_url configured[/red]")
        raise typer.Exit(code=1)

    asyncio.run(_fetch_models(resolved_url))


async def _fetch_models(base_url: str) -> None:
    url = base_url.rstrip("/") + "/models"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError:
        rprint(f"[red]Error: could not connect to {base_url}[/red]")
        raise typer.Exit(code=1)
    except Exception as exc:
        rprint(f"[red]Error: {exc}[/red]")
        raise typer.Exit(code=1)

    model_list = data.get("data", [])
    if not model_list:
        rprint("[yellow]No models found.[/yellow]")
        return

    rprint(f"[bold]Models at {base_url}:[/bold]")
    for entry in model_list:
        rprint(f"  {entry['id']}")
