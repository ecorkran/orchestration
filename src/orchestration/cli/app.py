"""Typer CLI application definition for the orchestration framework."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="orchestration",
    help="Multi-agent orchestration CLI",
    no_args_is_help=True,
)
