"""Tests for the spawn CLI command."""

from __future__ import annotations

from unittest.mock import AsyncMock

from typer.testing import CliRunner

from orchestration.cli.app import app
from orchestration.core.agent_registry import (
    AgentAlreadyExistsError,
)
from orchestration.core.models import AgentConfig
from orchestration.providers.errors import ProviderAuthError, ProviderError
from tests.cli.conftest import make_agent_info

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke(runner: CliRunner, *args: str):  # type: ignore[no-untyped-def]
    return runner.invoke(app, ["spawn", *args])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSpawnCommand:
    def test_minimal_args_success(
        self, cli_runner: CliRunner, patch_registry: AsyncMock
    ) -> None:
        patch_registry.spawn.return_value = make_agent_info("test")
        result = _invoke(cli_runner, "--name", "test")
        assert result.exit_code == 0, result.output
        assert "test" in result.output

    def test_spawn_calls_registry_with_correct_config(
        self, cli_runner: CliRunner, patch_registry: AsyncMock
    ) -> None:
        patch_registry.spawn.return_value = make_agent_info("test")
        _invoke(
            cli_runner,
            "--name",
            "test",
            "--type",
            "sdk",
            "--provider",
            "sdk",
            "--cwd",
            "/tmp",
            "--system-prompt",
            "Be helpful",
            "--permission-mode",
            "acceptEdits",
        )
        patch_registry.spawn.assert_called_once()
        config: AgentConfig = patch_registry.spawn.call_args[0][0]
        assert config.name == "test"
        assert config.agent_type == "sdk"
        assert config.provider == "sdk"
        assert config.cwd == "/tmp"
        assert config.instructions == "Be helpful"
        assert config.permission_mode == "acceptEdits"

    def test_provider_defaults_to_type(
        self, cli_runner: CliRunner, patch_registry: AsyncMock
    ) -> None:
        patch_registry.spawn.return_value = make_agent_info("bot")
        _invoke(cli_runner, "--name", "bot", "--type", "sdk")
        config: AgentConfig = patch_registry.spawn.call_args[0][0]
        assert config.provider == "sdk"

    def test_duplicate_name_shows_error_and_exits_1(
        self, cli_runner: CliRunner, patch_registry: AsyncMock
    ) -> None:
        patch_registry.spawn.side_effect = AgentAlreadyExistsError("dup")
        result = _invoke(cli_runner, "--name", "dup")
        assert result.exit_code == 1
        assert "dup" in result.output
        assert "already exists" in result.output

    def test_provider_auth_error_shows_message_and_exits_1(
        self, cli_runner: CliRunner, patch_registry: AsyncMock
    ) -> None:
        patch_registry.spawn.side_effect = ProviderAuthError("bad creds")
        result = _invoke(cli_runner, "--name", "agent")
        assert result.exit_code == 1
        assert "Authentication failed" in result.output

    def test_provider_error_shows_message_and_exits_1(
        self, cli_runner: CliRunner, patch_registry: AsyncMock
    ) -> None:
        patch_registry.spawn.side_effect = ProviderError("boom")
        result = _invoke(cli_runner, "--name", "agent")
        assert result.exit_code == 1
        assert "Provider failed" in result.output

    def test_unknown_provider_shows_message_and_exits_1(
        self, cli_runner: CliRunner, patch_registry: AsyncMock
    ) -> None:
        patch_registry.spawn.side_effect = KeyError("no-such-provider")
        result = _invoke(
            cli_runner, "--name", "agent", "--provider", "no-such-provider"
        )
        assert result.exit_code == 1
        assert "Unknown provider" in result.output
