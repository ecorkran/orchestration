"""SDK Agent Provider using claude-agent-sdk."""

from __future__ import annotations

from squadron.providers.registry import register_provider
from squadron.providers.sdk.agent import SDKAgent
from squadron.providers.sdk.provider import SDKAgentProvider

# Auto-register on import.
_provider = SDKAgentProvider()
register_provider("sdk", _provider)

__all__ = ["SDKAgentProvider", "SDKAgent"]
