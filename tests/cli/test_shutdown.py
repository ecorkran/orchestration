"""Tests for the shutdown CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner

from orchestration.cli.app import app
from orchestration.core.agent_registry import AgentNotFoundError
from orchestration.core.models import ShutdownReport


def _invoke(runner: CliRunner, *args: str):  # type: ignore[no-untyped-def]
    return runner.invoke(app, ["shutdown", *args])


class TestShutdownCommand:
    def test_individual_shutdown_success(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        patch_registry.shutdown_agent.return_value = None
        result = _invoke(cli_runner, "myagent")
        assert result.exit_code == 0, result.output
        patch_registry.shutdown_agent.assert_called_once_with("myagent")
        assert "shut down" in result.output.lower()

    def test_individual_shutdown_agent_not_found(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        patch_registry.shutdown_agent.side_effect = AgentNotFoundError("ghost")
        result = _invoke(cli_runner, "ghost")
        assert result.exit_code == 1
        assert "No agent named" in result.output

    def test_bulk_shutdown_all_succeed(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        patch_registry.shutdown_all.return_value = ShutdownReport(
            succeeded=["a", "b"], failed={}
        )
        result = _invoke(cli_runner, "--all")
        assert result.exit_code == 0, result.output
        assert "2" in result.output
        assert "2 succeeded" in result.output

    def test_bulk_shutdown_with_failures_shows_details(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        patch_registry.shutdown_all.return_value = ShutdownReport(
            succeeded=["a"], failed={"b": "connection lost"}
        )
        result = _invoke(cli_runner, "--all")
        assert result.exit_code == 0, result.output
        assert "1 succeeded" in result.output
        assert "1 failed" in result.output
        assert "connection lost" in result.output

    def test_neither_name_nor_all_shows_error(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        result = _invoke(cli_runner)
        assert result.exit_code == 1
        assert "Provide" in result.output or "agent name" in result.output
