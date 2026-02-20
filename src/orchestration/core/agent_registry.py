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

    def list_agents(
        self,
        state: AgentState | None = None,
        provider: str | None = None,
    ) -> list[AgentInfo]:
        """Return AgentInfo summaries for all tracked agents, optionally filtered.

        Args:
            state: If given, include only agents in this state.
            provider: If given, include only agents from this provider.
        """
        result: list[AgentInfo] = []
        for name, agent in self._agents.items():
            agent_provider = self._configs[name].provider
            if state is not None and agent.state != state:
                continue
            if provider is not None and agent_provider != provider:
                continue
            result.append(
                AgentInfo(
                    name=agent.name,
                    agent_type=agent.agent_type,
                    provider=agent_provider,
                    state=agent.state,
                )
            )
        return result

    async def shutdown_agent(self, name: str) -> None:
        """Shut down the agent registered under *name* and remove it.

        The agent is always removed from the registry, even if ``agent.shutdown()``
        raises — an agent in an indeterminate state should not remain tracked.

        Raises:
            AgentNotFoundError: If no agent with *name* exists.
        """
        if name not in self._agents:
            raise AgentNotFoundError(f"Agent '{name}' not found in the registry")

        agent = self._agents[name]
        try:
            await agent.shutdown()
        except Exception:
            logger.warning(
                "agent.shutdown_failed: name=%s error=%s",
                name,
                str(agent),
                exc_info=True,
            )
            raise
        finally:
            del self._agents[name]
            del self._configs[name]

        logger.info("agent.shutdown: name=%s", name)
