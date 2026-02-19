"""Agent and AgentProvider Protocols — contracts for all provider implementations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from orchestration.core.models import AgentConfig, AgentState, Message


@runtime_checkable
class Agent(Protocol):
    """A participant that can receive and produce messages."""

    @property
    def name(self) -> str:
        """Agent display name."""
        ...

    @property
    def agent_type(self) -> str:
        """Execution model: "sdk" or "api"."""
        ...

    @property
    def state(self) -> AgentState:
        """Current lifecycle state."""
        ...

    def handle_message(self, message: Message) -> AsyncIterator[Message]:
        """Process an incoming message and yield response messages."""
        ...

    async def shutdown(self) -> None:
        """Gracefully shut down the agent."""
        ...


@runtime_checkable
class AgentProvider(Protocol):
    """Creates and manages agents of a specific type."""

    @property
    def provider_type(self) -> str:
        """Provider identifier: "sdk", "anthropic", "openai", etc."""
        ...

    async def create_agent(self, config: AgentConfig) -> Agent:
        """Create an agent from configuration."""
        ...

    async def validate_credentials(self) -> bool:
        """Check that credentials are valid and the provider is reachable."""
        ...
