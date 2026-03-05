"""OpenAI-Compatible Agent Provider."""

from __future__ import annotations

from squadron.providers.openai.agent import OpenAICompatibleAgent
from squadron.providers.openai.provider import OpenAICompatibleProvider
from squadron.providers.registry import register_provider

# Auto-register on import.
_provider = OpenAICompatibleProvider()
register_provider("openai", _provider)

__all__ = ["OpenAICompatibleProvider", "OpenAICompatibleAgent"]
