"""Tests for provider registry and LLMProvider Protocol."""

from __future__ import annotations

import pytest

from orchestration.core.models import ProviderConfig
from orchestration.providers import registry as reg_module
from orchestration.providers.base import LLMProvider
from orchestration.providers.registry import (
    get_provider,
    list_providers,
    register_provider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeProvider:
    """Minimal implementation satisfying LLMProvider structurally."""

    def __init__(self, config: ProviderConfig) -> None:
        self._name = config.provider
        self._model = config.model

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    async def send_message(self, messages, system=None):  # type: ignore[override]
        return "response"

    async def stream_message(self, messages, system=None):  # type: ignore[override]
        yield "chunk"

    async def validate(self) -> bool:
        return True


def _fake_factory(config: ProviderConfig) -> _FakeProvider:
    return _FakeProvider(config)


@pytest.fixture(autouse=True)
def _clean_registry() -> None:  # type: ignore[return]
    """Isolate registry state between tests."""
    original = dict(reg_module._REGISTRY)
    reg_module._REGISTRY.clear()
    yield
    reg_module._REGISTRY.clear()
    reg_module._REGISTRY.update(original)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_register_provider_adds_factory() -> None:
    register_provider("fake", _fake_factory)
    assert "fake" in list_providers()


def test_get_provider_invokes_factory() -> None:
    register_provider("fake", _fake_factory)
    config = ProviderConfig(provider="fake", model="fake-model")
    provider = get_provider("fake", config)
    assert provider.name == "fake"
    assert provider.model == "fake-model"


def test_get_provider_raises_for_unregistered() -> None:
    with pytest.raises(KeyError, match="unregistered"):
        config = ProviderConfig(provider="unregistered", model="m")
        get_provider("unregistered", config)


def test_list_providers_returns_registered_names() -> None:
    register_provider("provA", _fake_factory)
    register_provider("provB", _fake_factory)
    names = list_providers()
    assert "provA" in names
    assert "provB" in names


def test_llm_provider_protocol_structural() -> None:
    """_FakeProvider satisfies LLMProvider Protocol at runtime."""
    config = ProviderConfig(provider="fake", model="m")
    provider = _FakeProvider(config)
    assert isinstance(provider, LLMProvider)
