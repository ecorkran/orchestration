"""Shared fixtures for CLI tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from orchestration.core.models import AgentInfo, AgentState, Message


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CliRunner instance for invoking CLI commands in tests."""
    return CliRunner()


@pytest.fixture
def mock_daemon_client() -> MagicMock:
    """Mock DaemonClient with all async methods as AsyncMock."""
    client = MagicMock()
    client.spawn = AsyncMock()
    client.list_agents = AsyncMock()
    client.send_message = AsyncMock()
    client.get_history = AsyncMock()
    client.shutdown_agent = AsyncMock()
    client.shutdown_all = AsyncMock()
    client.health = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def patch_daemon_client(mock_daemon_client: MagicMock):  # type: ignore[no-untyped-def]
    """Patch DaemonClient() in all command modules to return mock."""
    targets = [
        "orchestration.cli.commands.spawn.DaemonClient",
        "orchestration.cli.commands.list.DaemonClient",
        "orchestration.cli.commands.task.DaemonClient",
        "orchestration.cli.commands.shutdown.DaemonClient",
    ]
    patches = []
    for t in targets:
        try:
            p = patch(t, return_value=mock_daemon_client)
            p.start()
            patches.append(p)
        except (ModuleNotFoundError, AttributeError):
            pass  # Module not yet created
    yield mock_daemon_client
    for p in patches:
        p.stop()


def make_agent_info(
    name: str = "test-agent",
    agent_type: str = "sdk",
    provider: str = "sdk",
    state: AgentState = AgentState.idle,
) -> AgentInfo:
    """Factory for AgentInfo test instances."""
    return AgentInfo(
        name=name,
        agent_type=agent_type,
        provider=provider,
        state=state,
    )


def make_agent_dict(
    name: str = "test-agent",
    agent_type: str = "sdk",
    provider: str = "sdk",
    state: str = "idle",
) -> dict:  # type: ignore[type-arg]
    """Factory for agent info dicts (daemon API response format)."""
    return {
        "name": name,
        "agent_type": agent_type,
        "provider": provider,
        "state": state,
    }


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


def make_message_dict(
    content: str = "Hello from agent",
    sender: str = "test-agent",
) -> dict:  # type: ignore[type-arg]
    """Factory for message dicts (daemon API response format)."""
    return {
        "id": "test-id",
        "sender": sender,
        "content": content,
        "message_type": "chat",
        "timestamp": "2026-02-28T00:00:00",
        "metadata": {},
    }
