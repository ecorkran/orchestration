"""Typer CLI application definition for the orchestration framework."""

from __future__ import annotations

import typer

from orchestration.cli.commands.list import list_agents
from orchestration.cli.commands.review import review_app
from orchestration.cli.commands.shutdown import shutdown
from orchestration.cli.commands.spawn import spawn
from orchestration.cli.commands.task import task

app = typer.Typer(
    name="orchestration",
    help="Multi-agent orchestration CLI",
    no_args_is_help=True,
)

app.command("spawn")(spawn)
app.command("list")(list_agents)
app.command("task")(task)
app.command("shutdown")(shutdown)
app.add_typer(review_app, name="review")
