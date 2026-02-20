"""Trivial smoke test verifying the CLI app responds to --help."""

from __future__ import annotations

from typer.testing import CliRunner

from orchestration.cli.app import app


def test_help_exits_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "orchestration" in result.output.lower()
