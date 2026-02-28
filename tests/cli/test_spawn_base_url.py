"""Tests for --base-url flag on spawn command (daemon client version)."""

from __future__ import annotations

from unittest.mock import MagicMock

from typer.testing import CliRunner

from orchestration.cli.app import app
from tests.cli.conftest import make_agent_dict


def _invoke(runner: CliRunner, *args: str):  # type: ignore[no-untyped-def]
    return runner.invoke(app, ["spawn", *args])


class TestBaseUrlFlag:
    def test_base_url_passed_to_spawn_request(
        self, cli_runner: CliRunner, patch_daemon_client: MagicMock
    ) -> None:
        patch_daemon_client.spawn.return_value = make_agent_dict("agent")
        _invoke(
            cli_runner,
            "--name",
            "agent",
            "--base-url",
            "http://localhost:11434/v1",
        )
        patch_daemon_client.spawn.assert_called_once()
        request_data = patch_daemon_client.spawn.call_args[0][0]
        assert request_data["base_url"] == "http://localhost:11434/v1"

    def test_base_url_defaults_to_none(
        self, cli_runner: CliRunner, patch_daemon_client: MagicMock
    ) -> None:
        patch_daemon_client.spawn.return_value = make_agent_dict("agent")
        _invoke(cli_runner, "--name", "agent")
        request_data = patch_daemon_client.spawn.call_args[0][0]
        assert request_data["base_url"] is None
