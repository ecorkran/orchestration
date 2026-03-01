"""Tests for CLI auth commands (auth login, auth status)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from orchestration.cli.app import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_auth_login_valid_key(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When env var is set, output shows ✓ and masked key."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-abcdef1234567890")
    result = runner.invoke(app, ["auth", "login", "openai"])
    assert result.exit_code == 0
    assert "✓" in result.output
    assert "OPENAI_API_KEY" in result.output
    assert "sk-" in result.output  # masked: first 3 chars
    assert "7890" in result.output  # masked: last 4


def test_auth_login_missing_key(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When env var is not set, output shows ✗ and hint."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = runner.invoke(app, ["auth", "login", "openai"])
    assert result.exit_code == 0
    assert "✗" in result.output
    assert "OPENAI_API_KEY is not set" in result.output
    assert "export OPENAI_API_KEY" in result.output


def test_auth_login_local_no_auth(runner: CliRunner) -> None:
    """Local profile reports no authentication required."""
    result = runner.invoke(app, ["auth", "login", "local"])
    assert result.exit_code == 0
    assert "No authentication required" in result.output
    assert "local" in result.output


def test_auth_login_unknown_profile(runner: CliRunner) -> None:
    """Unknown profile produces error message and exit code 1."""
    result = runner.invoke(app, ["auth", "login", "nonexistent-profile"])
    assert result.exit_code == 1
    assert "nonexistent-profile" in result.output or "Error" in result.output


def test_auth_status_shows_all_profiles(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Status output contains all built-in profile names."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "openai" in result.output
    assert "openrouter" in result.output
    assert "local" in result.output
    assert "gemini" in result.output


def test_auth_status_valid_and_missing(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Status shows ✓ for set keys and ✗ for missing keys."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-testkey")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "✓" in result.output  # at least one valid
    assert "✗" in result.output  # at least one missing
