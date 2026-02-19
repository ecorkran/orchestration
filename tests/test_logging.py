"""Tests for structured logging configuration."""

from __future__ import annotations

import json
import logging

import pytest

from orchestration.config import Settings
from orchestration.logging import get_logger, setup_logging


def _make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


@pytest.fixture(autouse=True)
def _reset_root_logger() -> None:  # type: ignore[return]
    """Restore root logger state between tests."""
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    yield
    root.handlers.clear()
    root.handlers.extend(original_handlers)
    root.setLevel(original_level)


def test_get_logger_returns_logger_instance() -> None:
    logger = get_logger("orchestration.test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "orchestration.test"


def test_json_formatter_produces_valid_json(capfd: pytest.CaptureFixture[str]) -> None:
    settings = _make_settings(log_level="DEBUG", log_format="json")
    setup_logging(settings)
    logger = get_logger("test.json")
    logger.info("hello json")
    captured = capfd.readouterr()
    line = captured.err.strip()
    data = json.loads(line)
    assert data["level"] == "INFO"
    assert data["message"] == "hello json"
    assert "timestamp" in data
    assert "name" in data


def test_text_format_produces_readable_output(capfd: pytest.CaptureFixture[str]) -> None:
    settings = _make_settings(log_level="DEBUG", log_format="text")
    setup_logging(settings)
    logger = get_logger("test.text")
    logger.warning("hello text")
    captured = capfd.readouterr()
    line = captured.err.strip()
    assert "WARNING" in line
    assert "hello text" in line


def test_log_level_configuration() -> None:
    settings = _make_settings(log_level="WARNING", log_format="text")
    setup_logging(settings)
    root = logging.getLogger()
    assert root.level == logging.WARNING


def test_debug_level_configuration() -> None:
    settings = _make_settings(log_level="DEBUG", log_format="json")
    setup_logging(settings)
    root = logging.getLogger()
    assert root.level == logging.DEBUG
