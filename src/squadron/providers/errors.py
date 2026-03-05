"""Shared exception hierarchy for all provider implementations."""

from __future__ import annotations


class ProviderError(Exception):
    """Base exception for all provider errors."""


class ProviderAuthError(ProviderError):
    """Authentication or credential errors."""


class ProviderAPIError(ProviderError):
    """Errors from the underlying LLM API (rate limits, server errors, etc.)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ProviderTimeoutError(ProviderError):
    """Request timeout errors."""
