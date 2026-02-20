"""Tests for the list CLI command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from typer.testing import CliRunner

from orchestration.cli.app import app
from orchestration.core.models import AgentState
from tests.cli.conftest import make_agent_info


def _invoke(runner: CliRunner, *args: str):  # type: ignore[no-untyped-def]
    return runner.invoke(app, ["list", *args])


class TestListCommand:
    def test_empty_registry_shows_no_agents_message(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        patch_registry.list_agents.return_value = []
        result = _invoke(cli_runner)
        assert result.exit_code == 0, result.output
        assert "No agents running" in result.output

    def test_two_agents_output_contains_names_and_details(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        patch_registry.list_agents.return_value = [
            make_agent_info("agent-one", agent_type="sdk", provider="sdk"),
            make_agent_info("agent-two", agent_type="sdk", provider="sdk"),
        ]
        result = _invoke(cli_runner)
        assert result.exit_code == 0, result.output
        assert "agent-one" in result.output
        assert "agent-two" in result.output
        assert "sdk" in result.output

    def test_filter_by_state_passes_state_to_list_agents(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        patch_registry.list_agents.return_value = []
        _invoke(cli_runner, "--state", "idle")
        patch_registry.list_agents.assert_called_once_with(
            state=AgentState.idle, provider=None
        )

    def test_filter_by_provider_passes_provider_to_list_agents(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        patch_registry.list_agents.return_value = []
        _invoke(cli_runner, "--provider", "sdk")
        patch_registry.list_agents.assert_called_once_with(
            state=None, provider="sdk"
        )

    def test_state_values_appear_in_output(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        patch_registry.list_agents.return_value = [
            make_agent_info("idle-bot", state=AgentState.idle),
            make_agent_info("busy-bot", state=AgentState.processing),
        ]
        result = _invoke(cli_runner)
        assert result.exit_code == 0, result.output
        assert "idle" in result.output
        assert "processing" in result.output
