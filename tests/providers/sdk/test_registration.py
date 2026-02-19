"""Integration tests for SDK provider auto-registration flow."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from orchestration.providers import registry as reg_module
from orchestration.providers.registry import get_provider, list_providers


@pytest.fixture(autouse=True)
def _clean_registry() -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    """Save and restore registry state so tests are isolated."""
    original = dict(reg_module._REGISTRY)  # pyright: ignore[reportPrivateUsage]
    reg_module._REGISTRY.clear()  # pyright: ignore[reportPrivateUsage]
    yield
    reg_module._REGISTRY.clear()  # pyright: ignore[reportPrivateUsage]
    reg_module._REGISTRY.update(original)  # pyright: ignore[reportPrivateUsage]


def _import_sdk_package() -> None:
    """Force the SDK package import and its auto-registration side effect."""
    import orchestration.providers.sdk  # noqa: F401
    from orchestration.providers.registry import register_provider

    # Re-register since the fixture clears the registry before each test.
    from orchestration.providers.sdk.provider import SDKAgentProvider

    register_provider("sdk", SDKAgentProvider())


class TestAutoRegistration:
    def test_sdk_in_list_providers(self) -> None:
        _import_sdk_package()
        assert "sdk" in list_providers()

    def test_get_provider_returns_sdk_provider(self) -> None:
        _import_sdk_package()
        provider = get_provider("sdk")
        from orchestration.providers.sdk.provider import SDKAgentProvider

        assert isinstance(provider, SDKAgentProvider)

    def test_provider_type_is_sdk(self) -> None:
        _import_sdk_package()
        assert get_provider("sdk").provider_type == "sdk"

    @pytest.mark.asyncio
    async def test_full_flow_create_agent(self) -> None:
        _import_sdk_package()
        from orchestration.core.models import AgentConfig
        from orchestration.providers.sdk.agent import SDKAgent

        provider = get_provider("sdk")
        config = AgentConfig(name="integration-test", agent_type="sdk", provider="sdk")
        agent = await provider.create_agent(config)
        assert isinstance(agent, SDKAgent)
        assert agent.name == "integration-test"
        assert agent.agent_type == "sdk"
