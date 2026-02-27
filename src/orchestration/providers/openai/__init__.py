"""OpenAI-Compatible Agent Provider."""

from __future__ import annotations

from orchestration.providers.openai.agent import OpenAICompatibleAgent
from orchestration.providers.openai.provider import OpenAICompatibleProvider
from orchestration.providers.registry import register_provider

# Auto-register on import.
_provider = OpenAICompatibleProvider()
register_provider("openai", _provider)

__all__ = ["OpenAICompatibleProvider", "OpenAICompatibleAgent"]
