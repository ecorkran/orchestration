"""Tests for core Pydantic models and enums."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from orchestration.core.models import (
    Agent,
    AgentState,
    Message,
    MessageType,
    ProviderConfig,
    TopologyConfig,
    TopologyType,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


def test_agent_state_values() -> None:
    assert AgentState.idle == "idle"
    assert AgentState.processing == "processing"
    assert AgentState.restarting == "restarting"
    assert AgentState.failed == "failed"
    assert AgentState.terminated == "terminated"
    assert len(AgentState) == 5


def test_message_type_values() -> None:
    assert MessageType.chat == "chat"
    assert MessageType.system == "system"
    assert MessageType.command == "command"
    assert len(MessageType) == 3


def test_topology_type_values() -> None:
    assert TopologyType.broadcast == "broadcast"
    assert TopologyType.filtered == "filtered"
    assert TopologyType.hierarchical == "hierarchical"
    assert TopologyType.custom == "custom"
    assert len(TopologyType) == 4


# ---------------------------------------------------------------------------
# Agent model tests
# ---------------------------------------------------------------------------


def test_agent_creation_with_required_fields() -> None:
    agent = Agent(
        name="test-bot",
        instructions="You are a helpful assistant.",
        provider="anthropic",
        model="claude-3-sonnet",
    )
    assert agent.name == "test-bot"
    assert agent.provider == "anthropic"
    assert agent.model == "claude-3-sonnet"


def test_agent_id_auto_generated() -> None:
    a1 = Agent(name="a", instructions="i", provider="p", model="m")
    a2 = Agent(name="a", instructions="i", provider="p", model="m")
    assert len(a1.id) == 36  # UUID format
    assert a1.id != a2.id


def test_agent_default_state() -> None:
    agent = Agent(name="a", instructions="i", provider="p", model="m")
    assert agent.state == AgentState.idle


def test_agent_default_created_at() -> None:
    before = datetime.now(UTC)
    agent = Agent(name="a", instructions="i", provider="p", model="m")
    after = datetime.now(UTC)
    assert before <= agent.created_at <= after


def test_agent_rejects_invalid_state() -> None:
    with pytest.raises(ValidationError):
        Agent(
            name="a",
            instructions="i",
            provider="p",
            model="m",
            state="invalid_state",  # type: ignore[arg-type]
        )


def test_agent_json_round_trip() -> None:
    agent = Agent(name="bot", instructions="sys", provider="anthropic", model="claude-3")
    data = agent.model_dump_json()
    restored = Agent.model_validate_json(data)
    assert restored.id == agent.id
    assert restored.name == agent.name
    assert restored.state == agent.state


# ---------------------------------------------------------------------------
# Message model tests
# ---------------------------------------------------------------------------


def test_message_creation_with_required_fields() -> None:
    msg = Message(sender="human", recipients=["all"], content="hello")
    assert msg.sender == "human"
    assert msg.recipients == ["all"]
    assert msg.content == "hello"


def test_message_id_auto_generated() -> None:
    m1 = Message(sender="s", recipients=["r"], content="c")
    m2 = Message(sender="s", recipients=["r"], content="c")
    assert len(m1.id) == 36
    assert m1.id != m2.id


def test_message_timestamp_auto_generated() -> None:
    before = datetime.now(UTC)
    msg = Message(sender="s", recipients=["r"], content="c")
    after = datetime.now(UTC)
    assert before <= msg.timestamp <= after


def test_message_default_message_type() -> None:
    msg = Message(sender="s", recipients=["r"], content="c")
    assert msg.message_type == MessageType.chat


def test_message_default_metadata() -> None:
    msg = Message(sender="s", recipients=["r"], content="c")
    assert msg.metadata == {}


def test_message_rejects_invalid_message_type() -> None:
    with pytest.raises(ValidationError):
        Message(
            sender="s",
            recipients=["r"],
            content="c",
            message_type="invalid",  # type: ignore[arg-type]
        )


def test_message_json_round_trip() -> None:
    msg = Message(sender="human", recipients=["agent1", "agent2"], content="hi")
    data = msg.model_dump_json()
    restored = Message.model_validate_json(data)
    assert restored.id == msg.id
    assert restored.recipients == msg.recipients
    assert restored.message_type == msg.message_type


# ---------------------------------------------------------------------------
# ProviderConfig model tests
# ---------------------------------------------------------------------------


def test_provider_config_required_fields() -> None:
    cfg = ProviderConfig(provider="anthropic", model="claude-3")
    assert cfg.provider == "anthropic"
    assert cfg.model == "claude-3"


def test_provider_config_optional_defaults() -> None:
    cfg = ProviderConfig(provider="anthropic", model="claude-3")
    assert cfg.api_key is None
    assert cfg.credential_path is None
    assert cfg.extra == {}


def test_provider_config_with_all_fields() -> None:
    cfg = ProviderConfig(
        provider="anthropic",
        model="claude-3",
        api_key="sk-test",
        credential_path="/path/to/cred",
        extra={"timeout": 30},
    )
    assert cfg.api_key == "sk-test"
    assert cfg.credential_path == "/path/to/cred"
    assert cfg.extra == {"timeout": 30}


def test_provider_config_json_round_trip() -> None:
    cfg = ProviderConfig(provider="anthropic", model="claude-3", api_key="key")
    data = cfg.model_dump_json()
    restored = ProviderConfig.model_validate_json(data)
    assert restored.provider == cfg.provider
    assert restored.api_key == cfg.api_key


# ---------------------------------------------------------------------------
# TopologyConfig model tests
# ---------------------------------------------------------------------------


def test_topology_config_defaults() -> None:
    tc = TopologyConfig()
    assert tc.topology_type == TopologyType.broadcast
    assert tc.config == {}


def test_topology_config_with_values() -> None:
    tc = TopologyConfig(topology_type=TopologyType.hierarchical, config={"root": "agent1"})
    assert tc.topology_type == TopologyType.hierarchical
    assert tc.config == {"root": "agent1"}


def test_topology_config_json_round_trip() -> None:
    tc = TopologyConfig(topology_type=TopologyType.filtered, config={"filter": "tag"})
    data = tc.model_dump_json()
    restored = TopologyConfig.model_validate_json(data)
    assert restored.topology_type == tc.topology_type
    assert restored.config == tc.config
