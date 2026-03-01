"""Tests for resolve_auth_strategy factory function."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from orchestration.core.models import AgentConfig
from orchestration.providers.auth import ApiKeyStrategy, resolve_auth_strategy
from orchestration.providers.errors import ProviderAuthError


def _make_config(**kwargs: object) -> AgentConfig:
    defaults: dict[str, object] = {
        "name": "test-agent",
        "agent_type": "api",
        "provider": "openai",
    }
    defaults.update(kwargs)
    return AgentConfig(**defaults)  # type: ignore[arg-type]


def test_resolve_api_key_strategy_default() -> None:
    """No profile → returns ApiKeyStrategy."""
    config = _make_config()
    strategy = resolve_auth_strategy(config, profile=None)
    assert isinstance(strategy, ApiKeyStrategy)


def test_resolve_api_key_strategy_with_profile() -> None:
    """Profile with auth_type='api_key' → ApiKeyStrategy using profile's api_key_env."""
    config = _make_config()
    profile = SimpleNamespace(auth_type="api_key", api_key_env="MY_PROFILE_KEY")
    strategy = resolve_auth_strategy(config, profile=profile)  # type: ignore[arg-type]
    assert isinstance(strategy, ApiKeyStrategy)
    # Verify the env_var was taken from the profile
    assert strategy._env_var == "MY_PROFILE_KEY"


def test_resolve_unknown_auth_type_raises() -> None:
    """Profile with auth_type='unknown' → ProviderAuthError with descriptive message."""
    config = _make_config()
    profile = SimpleNamespace(auth_type="unknown", api_key_env=None)
    with pytest.raises(ProviderAuthError, match="Unknown auth_type 'unknown'"):
        resolve_auth_strategy(config, profile=profile)  # type: ignore[arg-type]


def test_resolve_no_profile_uses_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config with credentials api_key_env and no profile → strategy uses that env var."""  # noqa: E501
    monkeypatch.setenv("MY_KEY", "resolved-from-credentials")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = _make_config(credentials={"api_key_env": "MY_KEY"})
    strategy = resolve_auth_strategy(config, profile=None)
    assert isinstance(strategy, ApiKeyStrategy)
    assert strategy._env_var == "MY_KEY"

    import asyncio

    result = asyncio.run(strategy.get_credentials())
    assert result == {"api_key": "resolved-from-credentials"}
