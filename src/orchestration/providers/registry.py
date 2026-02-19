"""Provider registry — maps provider names to factory callables."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from orchestration.core.models import ProviderConfig
from orchestration.providers.base import LLMProvider

# Module-level registry: provider name -> factory(config) -> LLMProvider
_REGISTRY: dict[str, Callable[[ProviderConfig], LLMProvider]] = {}


def register_provider(name: str, factory: Callable[[ProviderConfig], Any]) -> None:
    """Register a factory function under the given provider name."""
    _REGISTRY[name] = factory


def get_provider(name: str, config: ProviderConfig) -> LLMProvider:
    """Look up and instantiate a provider by name.

    Raises:
        KeyError: If no provider is registered under *name*.
    """
    if name not in _REGISTRY:
        registered = list(_REGISTRY.keys())
        raise KeyError(
            f"Provider '{name}' is not registered. Available providers: {registered}"
        )
    return _REGISTRY[name](config)


def list_providers() -> list[str]:
    """Return the names of all currently registered providers."""
    return list(_REGISTRY.keys())
