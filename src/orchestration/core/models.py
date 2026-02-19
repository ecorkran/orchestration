"""Core Pydantic models for the orchestration framework."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentState(StrEnum):
    """Lifecycle states for a managed agent."""

    idle = "idle"
    processing = "processing"
    restarting = "restarting"
    failed = "failed"
    terminated = "terminated"


class MessageType(StrEnum):
    """Classification of messages routed through the message bus."""

    chat = "chat"
    system = "system"
    command = "command"


class TopologyType(StrEnum):
    """Communication topology strategy for agent routing."""

    broadcast = "broadcast"
    filtered = "filtered"
    hierarchical = "hierarchical"
    custom = "custom"


class Agent(BaseModel):
    """Represents a managed LLM agent instance."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    instructions: str
    provider: str
    model: str
    state: AgentState = AgentState.idle
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Message(BaseModel):
    """A message routed between agents via the message bus."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    sender: str
    recipients: list[str]
    content: str
    message_type: MessageType = MessageType.chat
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    provider: str
    model: str
    api_key: str | None = None
    credential_path: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class TopologyConfig(BaseModel):
    """Configuration for the agent communication topology."""

    topology_type: TopologyType = TopologyType.broadcast
    config: dict[str, Any] = Field(default_factory=dict)
