"""LLMProvider Protocol — contract for all LLM provider implementations."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from orchestration.core.models import Message


@runtime_checkable
class LLMProvider(Protocol):
    """Structural protocol that all LLM provider implementations must satisfy."""

    @property
    def name(self) -> str:
        """Provider name (e.g. "anthropic", "openai")."""
        ...

    @property
    def model(self) -> str:
        """Default model identifier for this provider."""
        ...

    async def send_message(
        self,
        messages: list[Message],
        system: str | None = None,
    ) -> str:
        """Send messages and return the complete response text."""
        ...

    async def stream_message(
        self,
        messages: list[Message],
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream the response, yielding text chunks as they arrive."""
        ...

    async def validate(self) -> bool:
        """Validate that the provider is configured and reachable."""
        ...
