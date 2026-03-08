"""Tests for the --version CLI flag."""

from __future__ import annotations

import importlib.metadata

from typer.testing import CliRunner

from squadron.cli.app import app

runner = CliRunner()


def test_version_outputs_squadron_and_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert "squadron" in result.output
    expected = importlib.metadata.version("squadron-ai")
    assert expected in result.output


def test_version_exits_zero() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
