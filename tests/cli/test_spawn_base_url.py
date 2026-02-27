"""Tests for --base-url flag on spawn command (T14-T15)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from typer.testing import CliRunner

from orchestration.cli.app import app
from orchestration.core.models import AgentConfig
from tests.cli.conftest import make_agent_info


def _invoke(runner: CliRunner, *args: str):  # type: ignore[no-untyped-def]
    return runner.invoke(app, ["spawn", *args])


class TestBaseUrlFlag:
    def test_base_url_passed_to_agent_config(
        self, cli_runner: CliRunner, patch_registry: AsyncMock
    ) -> None:
        patch_registry.spawn.return_value = make_agent_info("agent")
        _invoke(
            cli_runner,
            "--name", "agent",
            "--base-url", "http://localhost:11434/v1",
        )
        patch_registry.spawn.assert_called_once()
        config: AgentConfig = patch_registry.spawn.call_args[0][0]
        assert config.base_url == "http://localhost:11434/v1"

    def test_base_url_defaults_to_none(
        self, cli_runner: CliRunner, patch_registry: AsyncMock
    ) -> None:
        patch_registry.spawn.return_value = make_agent_info("agent")
        _invoke(cli_runner, "--name", "agent")
        config: AgentConfig = patch_registry.spawn.call_args[0][0]
        assert config.base_url is None
