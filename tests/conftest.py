"""Shared pytest fixtures for the orchestration test suite."""

from __future__ import annotations

import pytest

from orchestration.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Settings instance with test defaults, ignoring any .env file on disk."""
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        anthropic_api_key="test-api-key",
        log_level="DEBUG",
        log_format="text",
    )
