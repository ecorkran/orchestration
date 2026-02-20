"""Tests for AgentRegistry — spawn, lookup, shutdown, and singleton."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from orchestration.core.agent_registry import (
    AgentAlreadyExistsError,
    AgentNotFoundError,
    AgentRegistry,
)
from orchestration.core.models import AgentConfig, AgentState, Message
from orchestration.providers.errors import ProviderError
from orchestration.providers.registry import register_provider
from orchestration.providers.registry import _REGISTRY as _PROVIDER_REGISTRY


# ---------------------------------------------------------------------------
# Mock implementations satisfying Agent and AgentProvider Protocols
# ---------------------------------------------------------------------------


class MockAgent:
    """Test double satisfying the Agent Protocol."""

    def __init__(self, name: str, agent_type: str = "sdk") -> None:
        self._name = name
        self._agent_type = agent_type
        self._state = AgentState.idle
        self.shutdown_called = False
        self.shutdown_error: Exception | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def agent_type(self) -> str:
        return self._agent_type

    @property
    def state(self) -> AgentState:
        return self._state

    async def handle_message(self, message: Message) -> AsyncIterator[Message]:
        yield message  # pragma: no cover

    async def shutdown(self) -> None:
        self.shutdown_called = True
        if self.shutdown_error is not None:
            raise self.shutdown_error


class MockProvider:
    """Test double satisfying the AgentProvider Protocol."""

    def __init__(
        self,
        provider_type: str = "mock",
        *,
        create_error: Exception | None = None,
    ) -> None:
        self._provider_type = provider_type
        self._create_error = create_error
        self.created_agents: list[MockAgent] = []

    @property
    def provider_type(self) -> str:
        return self._provider_type

    async def create_agent(self, config: AgentConfig) -> MockAgent:
        if self._create_error is not None:
            raise self._create_error
        agent = MockAgent(name=config.name, agent_type=config.agent_type)
        self.created_agents.append(agent)
        return agent

    async def validate_credentials(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def registry(mock_provider: MockProvider) -> AgentRegistry:
    """Fresh AgentRegistry with a mock provider registered; cleaned up after test."""
    register_provider("mock", mock_provider)
    yield AgentRegistry()  # type: ignore[misc]
    _PROVIDER_REGISTRY.pop("mock", None)


def _config(name: str = "agent1", provider: str = "mock") -> AgentConfig:
    """Helper to build a minimal AgentConfig."""
    return AgentConfig(name=name, agent_type="sdk", provider=provider)


# ---------------------------------------------------------------------------
# Spawn and lookup tests (Tasks 4-5)
# ---------------------------------------------------------------------------


class TestSpawn:
    async def test_spawn_returns_agent_and_tracks_it(
        self, registry: AgentRegistry
    ) -> None:
        agent = await registry.spawn(_config("bot"))
        assert agent.name == "bot"
        assert registry.has("bot")
        assert registry.get("bot") is agent

    async def test_spawn_stores_agent_with_correct_name(
        self, registry: AgentRegistry
    ) -> None:
        await registry.spawn(_config("my-agent"))
        retrieved = registry.get("my-agent")
        assert retrieved.name == "my-agent"

    async def test_spawn_duplicate_name_raises(
        self, registry: AgentRegistry
    ) -> None:
        await registry.spawn(_config("dup"))
        with pytest.raises(AgentAlreadyExistsError, match="dup"):
            await registry.spawn(_config("dup"))

    async def test_spawn_unregistered_provider_raises_key_error(
        self, registry: AgentRegistry
    ) -> None:
        with pytest.raises(KeyError, match="no-such-provider"):
            await registry.spawn(_config("x", provider="no-such-provider"))

    async def test_spawn_provider_error_propagates_and_agent_not_stored(
        self, registry: AgentRegistry
    ) -> None:
        error_provider = MockProvider(
            provider_type="broken", create_error=ProviderError("boom")
        )
        register_provider("broken", error_provider)
        try:
            with pytest.raises(ProviderError, match="boom"):
                await registry.spawn(_config("fail-agent", provider="broken"))
            assert not registry.has("fail-agent")
        finally:
            _PROVIDER_REGISTRY.pop("broken", None)

    async def test_get_unknown_name_raises(self, registry: AgentRegistry) -> None:
        with pytest.raises(AgentNotFoundError, match="ghost"):
            registry.get("ghost")

    async def test_has_returns_false_for_unknown(
        self, registry: AgentRegistry
    ) -> None:
        assert not registry.has("nonexistent")
