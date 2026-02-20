"""Shared fixtures for CLI tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from orchestration.core.agent_registry import AgentRegistry
from orchestration.core.models import AgentConfig, AgentInfo, AgentState, Message


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CliRunner instance for invoking CLI commands in tests."""
    return CliRunner()


@pytest.fixture
def mock_registry() -> MagicMock:
    """Mock AgentRegistry with async methods patched as AsyncMock."""
    registry = MagicMock(spec=AgentRegistry)
    registry.spawn = AsyncMock()
    registry.shutdown_agent = AsyncMock()
    registry.shutdown_all = AsyncMock()
    return registry


@pytest.fixture
def patch_registry(mock_registry: MagicMock):  # type: ignore[no-untyped-def]
    """Patch get_registry() in all command modules to return mock_registry."""
    targets = [
        "orchestration.cli.commands.spawn.get_registry",
        "orchestration.cli.commands.list.get_registry",
        "orchestration.cli.commands.task.get_registry",
        "orchestration.cli.commands.shutdown.get_registry",
    ]
    patches = [patch(t, return_value=mock_registry) for t in targets]
    for p in patches:
        p.start()
    yield mock_registry
    for p in patches:
        p.stop()


def make_agent_info(
    name: str = "test-agent",
    agent_type: str = "sdk",
    provider: str = "sdk",
    state: AgentState = AgentState.idle,
) -> AgentInfo:
    """Factory for AgentInfo test instances."""
    return AgentInfo(name=name, agent_type=agent_type, provider=provider, state=state)


def make_message(
    content: str = "Hello from agent",
    sender: str = "test-agent",
) -> Message:
    """Factory for Message test instances."""
    return Message(
        sender=sender,
        recipients=["human"],
        content=content,
    )


def make_async_iter(*messages: Message) -> AsyncMock:
    """Return an async mock that iterates over the given messages."""

    async def _gen() -> AsyncIterator[Message]:
        for msg in messages:
            yield msg

    mock = MagicMock()
    mock.__aiter__ = lambda self: _gen()
    return mock
