"""Tests for Settings configuration loading."""

from __future__ import annotations

import pytest

from orchestration.config import Settings


def _settings(**overrides: object) -> Settings:
    """Create a Settings instance ignoring any .env file on disk."""
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_settings_default_values() -> None:
    s = _settings()
    assert s.default_provider == "anthropic"
    assert s.default_model == "claude-sonnet-4-20250514"
    assert s.anthropic_api_key is None
    assert s.anthropic_credential_path is None
    assert s.log_level == "INFO"
    assert s.log_format == "json"
    assert s.host == "127.0.0.1"
    assert s.port == 8000


def test_settings_picks_up_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCH_ANTHROPIC_API_KEY", "sk-test-key")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.anthropic_api_key == "sk-test-key"


def test_settings_log_level_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCH_LOG_LEVEL", "DEBUG")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.log_level == "DEBUG"


def test_settings_log_format_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCH_LOG_FORMAT", "text")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.log_format == "text"


def test_settings_port_parsed_as_int(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCH_PORT", "9090")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.port == 9090
    assert isinstance(s.port, int)
