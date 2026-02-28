"""Tests for OrchestrationEngine — agent lifecycle and conversation history."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from orchestration.core.models import AgentConfig


@pytest.fixture
def spawn_config() -> AgentConfig:
    """Minimal config for spawning a mock agent."""
    return AgentConfig(
        name="test-agent",
        agent_type="api",
        provider="mock",
        model="test-model",
    )


async def test_spawn_agent(engine, spawn_config):
    """Spawn via engine returns AgentInfo with correct name."""
    info = await engine.spawn_agent(spawn_config)
    assert info.name == "test-agent"
    assert info.provider == "mock"
    assert info.agent_type == "api"


async def test_spawn_agent_loads_provider(engine, spawn_config):
    """spawn_agent calls _load_provider with provider name before registry spawn."""
    with patch("orchestration.server.engine._load_provider") as mock_load:
        await engine.spawn_agent(spawn_config)
        mock_load.assert_called_once_with("mock")


async def test_list_agents_returns_spawned(engine):
    """Spawn two agents, list returns both."""
    config1 = AgentConfig(
        name="agent-a", agent_type="api", provider="mock", model="m"
    )
    config2 = AgentConfig(
        name="agent-b", agent_type="api", provider="mock", model="m"
    )
    await engine.spawn_agent(config1)
    await engine.spawn_agent(config2)

    agents = engine.list_agents()
    names = [a.name for a in agents]
    assert "agent-a" in names
    assert "agent-b" in names
    assert len(agents) == 2


async def test_send_message_returns_responses(engine, spawn_config):
    """Spawn, send message, get list of response Messages."""
    await engine.spawn_agent(spawn_config)
    responses = await engine.send_message("test-agent", "hello")
    assert len(responses) >= 1
    assert responses[0].content == "mock response"


async def test_send_message_records_history(engine, spawn_config):
    """After send, get_history returns both human and agent messages."""
    await engine.spawn_agent(spawn_config)
    await engine.send_message("test-agent", "hello")

    history = engine.get_history("test-agent")
    assert len(history) >= 2
    # First message is human input
    assert history[0].sender == "human"
    assert history[0].content == "hello"
    # Second is agent response
    assert history[1].sender == "test-agent"


async def test_get_history_empty_for_unknown(engine):
    """Returns empty list (not error) for unknown agent name."""
    history = engine.get_history("nonexistent")
    assert history == []


async def test_history_retained_after_shutdown(engine, spawn_config):
    """Spawn, message, shutdown — history still returns messages."""
    await engine.spawn_agent(spawn_config)
    await engine.send_message("test-agent", "hello")
    await engine.shutdown_agent("test-agent")

    history = engine.get_history("test-agent")
    assert len(history) >= 2
    assert history[0].sender == "human"
    assert history[1].sender == "test-agent"


async def test_shutdown_agent(engine, spawn_config):
    """Spawn then shutdown; agent no longer in list."""
    await engine.spawn_agent(spawn_config)
    assert len(engine.list_agents()) == 1

    await engine.shutdown_agent("test-agent")
    assert len(engine.list_agents()) == 0


async def test_shutdown_all(engine):
    """Spawn two, shutdown_all returns ShutdownReport with both names."""
    config1 = AgentConfig(
        name="agent-a", agent_type="api", provider="mock", model="m"
    )
    config2 = AgentConfig(
        name="agent-b", agent_type="api", provider="mock", model="m"
    )
    await engine.spawn_agent(config1)
    await engine.spawn_agent(config2)

    report = await engine.shutdown_all()
    assert "agent-a" in report.succeeded
    assert "agent-b" in report.succeeded
    assert len(report.failed) == 0
