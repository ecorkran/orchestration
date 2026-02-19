"""SDK Agent Provider using claude-agent-sdk."""

from __future__ import annotations

from orchestration.providers.registry import register_provider
from orchestration.providers.sdk.agent import SDKAgent
from orchestration.providers.sdk.provider import SDKAgentProvider

# Auto-register on import.
_provider = SDKAgentProvider()
register_provider("sdk", _provider)

__all__ = ["SDKAgentProvider", "SDKAgent"]
