"""review subcommand — execute review workflows via templates."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from orchestration.config.manager import get_config
from orchestration.review.models import ReviewResult, Severity, Verdict
from orchestration.review.runner import run_review
from orchestration.review.templates import (
    get_template,
    list_templates,
    load_builtin_templates,
)

review_app = typer.Typer(
    name="review",
    help="Run review workflows using built-in templates.",
    no_args_is_help=True,
)

_VERDICT_COLORS: dict[Verdict, str] = {
    Verdict.PASS: "bright_green",
    Verdict.CONCERNS: "yellow",
    Verdict.FAIL: "red",
    Verdict.UNKNOWN: "dim",
}

_SEVERITY_COLORS: dict[Severity, str] = {
    Severity.PASS: "bright_green",
    Severity.CONCERN: "yellow",
    Severity.FAIL: "red",
}


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def display_result(
    result: ReviewResult,
    output_mode: str,
    output_path: str | None,
    verbosity: int = 0,
) -> None:
    """Format and deliver review results based on output mode."""
    match output_mode:
        case "terminal":
            _display_terminal(result, verbosity)
        case "json":
            _display_json(result)
        case "file":
            _write_file(result, output_path)
        case _:
            rprint(f"[red]Unknown output mode: {output_mode}[/red]")
            raise typer.Exit(code=1)


def _display_terminal(result: ReviewResult, verbosity: int = 0) -> None:
    """Rich-formatted terminal output with verbosity levels.

    Level 0: verdict badge + finding headings with severity
    Level 1: above + full finding descriptions
    Level 2: above + raw output (tool usage details)
    """
    console = Console()
    color = _VERDICT_COLORS.get(result.verdict, "dim")

    header = Text(f"Review: {result.template_name}", style="bold")
    header.append("  Verdict: ", style="dim")
    header.append(result.verdict.value, style=f"bold {color}")

    console.print(Panel(header, expand=False))

    if not result.findings:
        console.print("  No specific findings.", style="dim")
        if verbosity >= 2 and result.raw_output:
            console.print()
            console.rule("Raw Output", style="dim")
            console.print(result.raw_output)
        return

    for finding in result.findings:
        sev_color = _SEVERITY_COLORS.get(finding.severity, "dim")
        console.print(
            f"  [{sev_color}][{finding.severity.value}][/{sev_color}] "
            f"[bold white]{finding.title}[/bold white]"
        )
        if verbosity >= 1 and finding.description:
            for line in finding.description.split("\n"):
                console.print(f"    {line}")
        if verbosity >= 1 and finding.file_ref:
            console.print(f"    -> {finding.file_ref}", style="cyan")

    if verbosity >= 2 and result.raw_output:
        console.print()
        console.rule("Raw Output", style="dim")
        console.print(result.raw_output)


def _display_json(result: ReviewResult) -> None:
    """JSON output to stdout."""
    typer.echo(json.dumps(result.to_dict(), indent=2))


def _write_file(result: ReviewResult, output_path: str | None) -> None:
    """Write JSON to file."""
    if not output_path:
        rprint("[red]Error: --output file requires a path argument.[/red]")
        raise typer.Exit(code=1)
    path = Path(output_path)
    path.write_text(json.dumps(result.to_dict(), indent=2))
    rprint(f"[green]Review result written to {path}[/green]")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _resolve_verbosity(verbose: int) -> int:
    """Resolve verbosity: CLI flag overrides config default."""
    if verbose > 0:
        return verbose
    config_val = get_config("verbosity")
    if isinstance(config_val, int):
        return config_val
    return 0


def _run_review_command(
    template_name: str,
    inputs: dict[str, str],
    output: str,
    output_path: str | None,
    verbosity: int = 0,
) -> None:
    """Common logic for running a review and displaying results."""
    load_builtin_templates()
    template = get_template(template_name)
    if template is None:
        available = [t.name for t in list_templates()]
        rprint(
            f"[red]Error: Unknown template '{template_name}'."
            f" Available: {available}[/red]"
        )
        raise typer.Exit(code=1)

    # Validate required inputs
    for req in template.required_inputs:
        if req.name not in inputs:
            rprint(
                f"[red]Error: Missing required input '{req.name}'"
                f" for template '{template_name}'.[/red]"
            )
            raise typer.Exit(code=1)

    try:
        result = asyncio.run(_execute_review(template_name, inputs))
    except Exception as exc:
        rprint(f"[red]Error: Review failed — {exc}[/red]")
        raise typer.Exit(code=1) from exc

    display_result(result, output, output_path, verbosity)

    # Exit with non-zero if review has failures
    if result.verdict == Verdict.FAIL:
        raise typer.Exit(code=2)


async def _execute_review(
    template_name: str,
    inputs: dict[str, str],
) -> ReviewResult:
    """Execute the review asynchronously."""
    load_builtin_templates()
    template = get_template(template_name)
    assert template is not None
    return await run_review(template, inputs)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@review_app.command("arch")
def review_arch(
    input_file: str = typer.Argument(help="Document to review"),
    against: str = typer.Option(
        ..., "--against", help="Architecture document to review against"
    ),
    cwd: str = typer.Option(".", "--cwd", help="Working directory"),
    verbose: int = typer.Option(
        0, "--verbose", "-v", count=True, help="Verbosity level (-v, -vv)"
    ),
    output: str = typer.Option(
        "terminal", "--output", help="Output format: terminal, json, file"
    ),
    output_path: str | None = typer.Option(
        None, "--output-path", help="File path for --output file"
    ),
) -> None:
    """Run an architectural review."""
    verbosity = _resolve_verbosity(verbose)
    inputs = {"input": input_file, "against": against, "cwd": cwd}
    _run_review_command("arch", inputs, output, output_path, verbosity)


@review_app.command("tasks")
def review_tasks(
    input_file: str = typer.Argument(help="Task breakdown file to review"),
    against: str = typer.Option(
        ..., "--against", help="Parent slice design to review against"
    ),
    cwd: str = typer.Option(".", "--cwd", help="Working directory"),
    verbose: int = typer.Option(
        0, "--verbose", "-v", count=True, help="Verbosity level (-v, -vv)"
    ),
    output: str = typer.Option(
        "terminal", "--output", help="Output format: terminal, json, file"
    ),
    output_path: str | None = typer.Option(
        None, "--output-path", help="File path for --output file"
    ),
) -> None:
    """Run a task plan review."""
    verbosity = _resolve_verbosity(verbose)
    inputs = {"input": input_file, "against": against, "cwd": cwd}
    _run_review_command("tasks", inputs, output, output_path, verbosity)


@review_app.command("code")
def review_code(
    cwd: str = typer.Option(".", "--cwd", help="Project directory to review"),
    files: str | None = typer.Option(
        None, "--files", help="Glob pattern to scope the review"
    ),
    diff: str | None = typer.Option(None, "--diff", help="Git ref to diff against"),
    verbose: int = typer.Option(
        0, "--verbose", "-v", count=True, help="Verbosity level (-v, -vv)"
    ),
    output: str = typer.Option(
        "terminal", "--output", help="Output format: terminal, json, file"
    ),
    output_path: str | None = typer.Option(
        None, "--output-path", help="File path for --output file"
    ),
) -> None:
    """Run a code review."""
    verbosity = _resolve_verbosity(verbose)
    inputs: dict[str, str] = {"cwd": cwd}
    if files:
        inputs["files"] = files
    if diff:
        inputs["diff"] = diff
    _run_review_command("code", inputs, output, output_path, verbosity)


@review_app.command("list")
def review_list() -> None:
    """List available review templates."""
    load_builtin_templates()
    templates = list_templates()
    if not templates:
        rprint("[dim]No templates available.[/dim]")
        return

    rprint("[bold]Available review templates:[/bold]")
    max_name_len = max(len(t.name) for t in templates)
    for t in templates:
        rprint(f"  {t.name:<{max_name_len}}  {t.description}")
