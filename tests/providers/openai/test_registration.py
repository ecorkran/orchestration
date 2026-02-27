"""Integration tests for OpenAI provider auto-registration flow."""

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


def _import_openai_package() -> None:
    """Force the OpenAI package import and its auto-registration side effect."""
    import importlib

    import orchestration.providers.openai  # noqa: F401

    # Re-register since the fixture clears the registry before each test.
    importlib.reload(orchestration.providers.openai)


class TestAutoRegistration:
    def test_openai_in_list_after_import(self) -> None:
        _import_openai_package()
        assert "openai" in list_providers()

    def test_get_provider_returns_openai_provider(self) -> None:
        _import_openai_package()
        from orchestration.providers.openai.provider import OpenAICompatibleProvider

        assert isinstance(get_provider("openai"), OpenAICompatibleProvider)

    def test_provider_type_is_openai(self) -> None:
        _import_openai_package()
        assert get_provider("openai").provider_type == "openai"
