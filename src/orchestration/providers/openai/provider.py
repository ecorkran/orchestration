"""OpenAICompatibleProvider implementation."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from orchestration.core.models import AgentConfig
from orchestration.logging import get_logger
from orchestration.providers.errors import ProviderAuthError, ProviderError

if TYPE_CHECKING:
    from orchestration.providers.openai.agent import OpenAICompatibleAgent

_log = get_logger("orchestration.providers.openai.provider")


class OpenAICompatibleProvider:
    """Creates API agents backed by the OpenAI Chat Completions API (or compatible)."""

    @property
    def provider_type(self) -> str:
        return "openai"

    async def create_agent(self, config: AgentConfig) -> OpenAICompatibleAgent:
        """Resolve credentials, construct AsyncOpenAI client, return agent."""
        api_key = config.api_key

        # Check profile-specified env var before falling back to OPENAI_API_KEY
        if not api_key:
            api_key_env = config.credentials.get("api_key_env")
            if api_key_env:
                api_key = os.environ.get(str(api_key_env))

        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:
            base_url = config.base_url or ""
            if base_url.startswith("http://localhost") or base_url.startswith(
                "http://127.0.0.1"
            ):
                api_key = "not-needed"
            else:
                raise ProviderAuthError(
                    "No API key found. Set config.api_key, the profile"
                    " api_key_env var, or OPENAI_API_KEY."
                )

        if config.model is None:
            raise ProviderError("model is required for OpenAI-compatible agents")

        default_headers = config.credentials.get("default_headers")
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url,
            default_headers=default_headers,  # type: ignore[arg-type]
        )

        from orchestration.providers.openai.agent import OpenAICompatibleAgent

        _log.debug("Creating OpenAI agent %r (model=%s)", config.name, config.model)
        return OpenAICompatibleAgent(
            name=config.name,
            client=client,
            model=config.model,
            system_prompt=config.instructions,
        )

    async def validate_credentials(self) -> bool:
        """Return True if openai is importable and OPENAI_API_KEY is set."""
        try:
            __import__("openai")
        except ImportError:
            return False
        return bool(os.environ.get("OPENAI_API_KEY"))
