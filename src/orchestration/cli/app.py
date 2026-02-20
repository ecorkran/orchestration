"""Typer CLI application definition for the orchestration framework."""

from __future__ import annotations

import typer

from orchestration.cli.commands import list as list_cmd
from orchestration.cli.commands import shutdown as shutdown_cmd
from orchestration.cli.commands import spawn as spawn_cmd
from orchestration.cli.commands import task as task_cmd

app = typer.Typer(
    name="orchestration",
    help="Multi-agent orchestration CLI",
    no_args_is_help=True,
)

app.add_typer(spawn_cmd.app, name="spawn")
app.add_typer(list_cmd.app, name="list")
app.add_typer(task_cmd.app, name="task")
app.add_typer(shutdown_cmd.app, name="shutdown")
