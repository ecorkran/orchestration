"""auth subcommand — credential validation and status reporting."""

from __future__ import annotations

import os

import typer
from rich import print as rprint
from rich.table import Table

from orchestration.providers.profiles import get_all_profiles, get_profile

auth_app = typer.Typer(
    name="auth",
    help="Credential management.",
    no_args_is_help=True,
)


def _mask_key(value: str) -> str:
    """Return a masked version of an API key: first 3 + last 4 chars."""
    if len(value) <= 7:
        return "***"
    return f"{value[:3]}...{value[-4:]}"


@auth_app.command("login")
def auth_login(
    profile_name: str = typer.Argument(help="Profile name to validate credentials for"),
) -> None:
    """Validate credentials for the given profile."""
    try:
        profile = get_profile(profile_name)
    except KeyError as exc:
        rprint(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if profile.api_key_env is None:
        rprint(
            f"[green]✓[/green] No authentication required for {profile_name} profile"
        )
        return

    value = os.environ.get(profile.api_key_env)
    if value:
        rprint(f"[green]✓[/green] {profile.api_key_env} is set ({_mask_key(value)})")
    else:
        rprint(f"[red]✗[/red] {profile.api_key_env} is not set")
        rprint(f"  Set it with: export {profile.api_key_env}=your-key-here")


@auth_app.command("status")
def auth_status() -> None:
    """Show credential state for all configured profiles."""
    profiles = get_all_profiles()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Profile")
    table.add_column("Auth Type")
    table.add_column("Status")
    table.add_column("Source")

    for name, profile in sorted(profiles.items()):
        if profile.api_key_env is None:
            status = "[green]✓ valid[/green]"
            source = "(no auth needed)"
        else:
            value = os.environ.get(profile.api_key_env)
            if value:
                status = "[green]✓ valid[/green]"
            else:
                status = "[red]✗ missing[/red]"
            source = profile.api_key_env

        table.add_row(name, profile.auth_type, status, source)

    rprint(table)
