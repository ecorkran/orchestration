"""Agent registry: spawn, track, and manage agent lifecycle."""

from __future__ import annotations


class AgentRegistryError(Exception):
    """Base for registry-specific errors."""


class AgentNotFoundError(AgentRegistryError):
    """Raised when referencing a non-existent agent name."""


class AgentAlreadyExistsError(AgentRegistryError):
    """Raised when spawning with a duplicate name."""


from orchestration.core.models import AgentConfig, AgentInfo, AgentState, ShutdownReport
from orchestration.logging import get_logger
from orchestration.providers.base import Agent
from orchestration.providers.registry import get_provider

logger = get_logger(__name__)


class AgentRegistry:
    """Central coordination point for agent lifecycle management.

    Spawns agents by provider configuration, tracks them by unique name,
    provides lookup/enumeration, and manages graceful shutdown.
    """

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}
        self._configs: dict[str, AgentConfig] = {}

    async def spawn(self, config: AgentConfig) -> Agent:
        """Create an agent from *config* and track it by name.

        Raises:
            AgentAlreadyExistsError: If an agent with *config.name* is already registered.
            KeyError: If the provider specified in *config.provider* is not registered.
            ProviderError: If the provider fails to create the agent.
        """
        if config.name in self._agents:
            raise AgentAlreadyExistsError(
                f"Agent '{config.name}' already exists in the registry"
            )

        provider = get_provider(config.provider)
        agent = await provider.create_agent(config)

        self._agents[config.name] = agent
        self._configs[config.name] = config

        logger.info(
            "agent.spawned: name=%s agent_type=%s provider=%s",
            config.name,
            config.agent_type,
            config.provider,
        )
        return agent

    def has(self, name: str) -> bool:
        """Return True if an agent with *name* is tracked."""
        return name in self._agents

    def get(self, name: str) -> Agent:
        """Return the Agent instance registered under *name*.

        Raises:
            AgentNotFoundError: If no agent with *name* exists.
        """
        if name not in self._agents:
            raise AgentNotFoundError(f"Agent '{name}' not found in the registry")
        return self._agents[name]
