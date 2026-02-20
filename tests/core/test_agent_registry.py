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


# ---------------------------------------------------------------------------
# list_agents tests (Tasks 6-7)
# ---------------------------------------------------------------------------


class TestListAgents:
    async def test_empty_registry_returns_empty_list(
        self, registry: AgentRegistry
    ) -> None:
        assert registry.list_agents() == []

    async def test_returns_agent_info_for_all_spawned(
        self, registry: AgentRegistry
    ) -> None:
        await registry.spawn(_config("a"))
        await registry.spawn(_config("b"))
        infos = registry.list_agents()
        assert len(infos) == 2
        names = {info.name for info in infos}
        assert names == {"a", "b"}
        for info in infos:
            assert info.agent_type == "sdk"
            assert info.provider == "mock"
            assert info.state == AgentState.idle

    async def test_filter_by_state(
        self, registry: AgentRegistry, mock_provider: MockProvider
    ) -> None:
        await registry.spawn(_config("idle-agent"))
        await registry.spawn(_config("busy-agent"))
        # Mutate one mock agent's state to processing
        mock_provider.created_agents[1]._state = AgentState.processing

        idle_only = registry.list_agents(state=AgentState.idle)
        assert len(idle_only) == 1
        assert idle_only[0].name == "idle-agent"

        processing_only = registry.list_agents(state=AgentState.processing)
        assert len(processing_only) == 1
        assert processing_only[0].name == "busy-agent"

    async def test_filter_by_provider(self, registry: AgentRegistry) -> None:
        other_provider = MockProvider(provider_type="other")
        register_provider("other", other_provider)
        try:
            await registry.spawn(_config("mock-agent", provider="mock"))
            await registry.spawn(_config("other-agent", provider="other"))

            mock_only = registry.list_agents(provider="mock")
            assert len(mock_only) == 1
            assert mock_only[0].name == "mock-agent"

            other_only = registry.list_agents(provider="other")
            assert len(other_only) == 1
            assert other_only[0].name == "other-agent"
        finally:
            _PROVIDER_REGISTRY.pop("other", None)

    async def test_combined_filters(
        self, registry: AgentRegistry, mock_provider: MockProvider
    ) -> None:
        other_provider = MockProvider(provider_type="other")
        register_provider("other", other_provider)
        try:
            await registry.spawn(_config("m1", provider="mock"))
            await registry.spawn(_config("m2", provider="mock"))
            await registry.spawn(_config("o1", provider="other"))
            # Set m2 to processing
            mock_provider.created_agents[1]._state = AgentState.processing

            result = registry.list_agents(
                state=AgentState.idle, provider="mock"
            )
            assert len(result) == 1
            assert result[0].name == "m1"
        finally:
            _PROVIDER_REGISTRY.pop("other", None)

    async def test_filter_with_no_matches_returns_empty(
        self, registry: AgentRegistry
    ) -> None:
        await registry.spawn(_config("agent"))
        assert registry.list_agents(state=AgentState.failed) == []
        assert registry.list_agents(provider="nonexistent") == []


# ---------------------------------------------------------------------------
# Individual shutdown tests (Tasks 8-9)
# ---------------------------------------------------------------------------


class TestShutdownAgent:
    async def test_shutdown_calls_agent_and_removes_it(
        self, registry: AgentRegistry, mock_provider: MockProvider
    ) -> None:
        await registry.spawn(_config("bot"))
        await registry.shutdown_agent("bot")
        assert mock_provider.created_agents[0].shutdown_called
        assert not registry.has("bot")

    async def test_after_shutdown_get_raises(
        self, registry: AgentRegistry
    ) -> None:
        await registry.spawn(_config("bot"))
        await registry.shutdown_agent("bot")
        with pytest.raises(AgentNotFoundError):
            registry.get("bot")

    async def test_shutdown_unknown_name_raises(
        self, registry: AgentRegistry
    ) -> None:
        with pytest.raises(AgentNotFoundError, match="ghost"):
            await registry.shutdown_agent("ghost")

    async def test_shutdown_error_still_removes_agent(
        self, registry: AgentRegistry, mock_provider: MockProvider
    ) -> None:
        await registry.spawn(_config("flaky"))
        mock_provider.created_agents[0].shutdown_error = RuntimeError("oops")
        with pytest.raises(RuntimeError, match="oops"):
            await registry.shutdown_agent("flaky")
        assert not registry.has("flaky")

    async def test_shutdown_error_has_returns_false(
        self, registry: AgentRegistry, mock_provider: MockProvider
    ) -> None:
        await registry.spawn(_config("flaky"))
        mock_provider.created_agents[0].shutdown_error = RuntimeError("oops")
        with pytest.raises(RuntimeError):
            await registry.shutdown_agent("flaky")
        assert not registry.has("flaky")
        with pytest.raises(AgentNotFoundError):
            registry.get("flaky")
