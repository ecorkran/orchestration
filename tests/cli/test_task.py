"""Tests for the task CLI command."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from typer.testing import CliRunner

from orchestration.cli.app import app
from orchestration.core.agent_registry import AgentNotFoundError
from orchestration.core.models import Message
from tests.cli.conftest import make_message


def _invoke(runner: CliRunner, *args: str):  # type: ignore[no-untyped-def]
    return runner.invoke(app, ["task", *args])


def _make_handle_message(*messages: Message) -> MagicMock:
    """Build a mock handle_message that yields the given messages."""

    async def _gen(_msg: Message) -> AsyncIterator[Message]:
        for m in messages:
            yield m

    mock = MagicMock(side_effect=_gen)
    return mock


class TestTaskCommand:
    def test_successful_task_shows_response_content(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        msg = make_message("Hello from agent")
        mock_agent = MagicMock()
        mock_agent.handle_message = _make_handle_message(msg)
        patch_registry.get.return_value = mock_agent

        result = _invoke(cli_runner, "myagent", "say hello")
        assert result.exit_code == 0, result.output
        assert "Hello from agent" in result.output

    def test_multiple_messages_all_appear_in_output(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        msgs = [make_message("First"), make_message("Second")]
        mock_agent = MagicMock()
        mock_agent.handle_message = _make_handle_message(*msgs)
        patch_registry.get.return_value = mock_agent

        result = _invoke(cli_runner, "myagent", "go")
        assert result.exit_code == 0, result.output
        assert "First" in result.output
        assert "Second" in result.output

    def test_agent_not_found_shows_error_and_exits_1(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        patch_registry.get.side_effect = AgentNotFoundError("ghost")
        result = _invoke(cli_runner, "ghost", "hello")
        assert result.exit_code == 1
        assert "No agent named" in result.output

    def test_query_called_with_correct_prompt(
        self, cli_runner: CliRunner, patch_registry: MagicMock
    ) -> None:
        msg = make_message("response")
        mock_agent = MagicMock()
        mock_agent.handle_message = _make_handle_message(msg)
        patch_registry.get.return_value = mock_agent

        _invoke(cli_runner, "myagent", "the-exact-prompt")

        # handle_message should have been called once; the message passed
        # must contain our prompt in its content
        assert mock_agent.handle_message.call_count == 1
        sent_message: Message = mock_agent.handle_message.call_args[0][0]
        assert sent_message.content == "the-exact-prompt"
