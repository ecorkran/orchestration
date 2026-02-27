"""Tests for providers/openai/provider.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestration.core.models import AgentConfig
from orchestration.providers.errors import ProviderAuthError, ProviderError
from orchestration.providers.openai.provider import OpenAICompatibleProvider

_BASE_CONFIG = dict(name="agent", agent_type="api", provider="openai", model="gpt-4o-mini")


@pytest.fixture
def provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider()


class TestProviderType:
    def test_provider_type(self, provider: OpenAICompatibleProvider) -> None:
        assert provider.provider_type == "openai"


class TestCreateAgent:
    @pytest.mark.asyncio
    async def test_uses_config_api_key(self, provider: OpenAICompatibleProvider) -> None:
        config = AgentConfig(**{**_BASE_CONFIG, "api_key": "sk-config"})
        with patch("orchestration.providers.openai.provider.AsyncOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            await provider.create_agent(config)
        mock_cls.assert_called_once()
        _, kwargs = mock_cls.call_args
        assert kwargs["api_key"] == "sk-config"

    @pytest.mark.asyncio
    async def test_falls_back_to_env_var(
        self, provider: OpenAICompatibleProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        config = AgentConfig(**{**_BASE_CONFIG, "api_key": None})
        with patch("orchestration.providers.openai.provider.AsyncOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            await provider.create_agent(config)
        _, kwargs = mock_cls.call_args
        assert kwargs["api_key"] == "sk-env"

    @pytest.mark.asyncio
    async def test_raises_auth_error_no_key(
        self, provider: OpenAICompatibleProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        config = AgentConfig(**{**_BASE_CONFIG, "api_key": None})
        with pytest.raises(ProviderAuthError):
            await provider.create_agent(config)

    @pytest.mark.asyncio
    async def test_raises_error_model_none(
        self, provider: OpenAICompatibleProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        config = AgentConfig(**{**_BASE_CONFIG, "model": None})
        with pytest.raises(ProviderError):
            await provider.create_agent(config)

    @pytest.mark.asyncio
    async def test_passes_base_url(
        self, provider: OpenAICompatibleProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        config = AgentConfig(**{**_BASE_CONFIG, "base_url": "http://localhost:11434/v1"})
        with patch("orchestration.providers.openai.provider.AsyncOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            await provider.create_agent(config)
        _, kwargs = mock_cls.call_args
        assert kwargs["base_url"] == "http://localhost:11434/v1"


class TestValidateCredentials:
    @pytest.mark.asyncio
    async def test_returns_true_when_key_set(
        self, provider: OpenAICompatibleProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-present")
        result = await provider.validate_credentials()
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_no_env(
        self, provider: OpenAICompatibleProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = await provider.validate_credentials()
        assert result is False

    @pytest.mark.asyncio
    async def test_never_raises(
        self, provider: OpenAICompatibleProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Should not raise even when openai is importable but key is absent
        result = await provider.validate_credentials()
        assert isinstance(result, bool)
