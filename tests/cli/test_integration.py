"""Integration smoke test: spawn → list → task → shutdown via real AgentRegistry."""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator

import pytest
from typer.testing import CliRunner

from orchestration.cli.app import app
from orchestration.core.agent_registry import reset_registry
from orchestration.core.models import AgentConfig, AgentState, Message
from orchestration.providers.registry import (
    _REGISTRY as _PROVIDER_REGISTRY,  # pyright: ignore[reportPrivateUsage]
)
from orchestration.providers.registry import register_provider

# ---------------------------------------------------------------------------
# Mock provider and agent satisfying Agent / AgentProvider Protocols
# ---------------------------------------------------------------------------


class _MockAgent:
    """Minimal Agent for integration testing — no SDK calls."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._state = AgentState.idle

    @property
    def name(self) -> str:
        return self._name

    @property
    def agent_type(self) -> str:
        return "sdk"

    @property
    def state(self) -> AgentState:
        return self._state

    async def handle_message(self, message: Message) -> AsyncIterator[Message]:
        yield Message(
            sender=self._name,
            recipients=["human"],
            content=f"echo: {message.content}",
        )

    async def shutdown(self) -> None:
        self._state = AgentState.terminated


class _MockProvider:
    """Minimal AgentProvider for integration testing."""

    @property
    def provider_type(self) -> str:
        return "sdk"

    async def create_agent(self, config: AgentConfig) -> _MockAgent:
        return _MockAgent(name=config.name)

    async def validate_credentials(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def integration_runner() -> Generator[CliRunner]:
    """CliRunner with a fresh registry and mock SDK provider."""
    reset_registry()
    mock_provider = _MockProvider()
    register_provider("sdk", mock_provider)

    yield CliRunner()

    reset_registry()
    _PROVIDER_REGISTRY.pop("sdk", None)


# ---------------------------------------------------------------------------
# Integration smoke test
# ---------------------------------------------------------------------------


def test_spawn_list_task_shutdown_sequence(
    integration_runner: CliRunner,
) -> None:
    runner = integration_runner

    # 1. Spawn agent
    result = runner.invoke(app, ["spawn", "--name", "test-agent", "--type", "sdk"])
    assert result.exit_code == 0, f"spawn failed:\n{result.output}"
    assert "test-agent" in result.output

    # 2. List: agent appears
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0, f"list failed:\n{result.output}"
    assert "test-agent" in result.output
    assert "idle" in result.output

    # 3. Task: send prompt, get echo response
    result = runner.invoke(app, ["task", "test-agent", "hello"])
    assert result.exit_code == 0, f"task failed:\n{result.output}"
    assert "echo: hello" in result.output

    # 4. Shutdown: agent removed
    result = runner.invoke(app, ["shutdown", "test-agent"])
    assert result.exit_code == 0, f"shutdown failed:\n{result.output}"
    assert "shut down" in result.output.lower()

    # 5. List again: no agents running
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0, f"second list failed:\n{result.output}"
    assert "No agents running" in result.output
