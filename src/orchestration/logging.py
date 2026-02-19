"""Structured logging configuration for the orchestration framework."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchestration.config import Settings

_LOG_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def setup_logging(settings: Settings) -> None:
    """Configure the root logger from *settings*.

    Idempotent — calling it multiple times with the same settings is safe.
    """
    global _LOG_CONFIGURED  # noqa: PLW0603

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Remove any existing handlers to avoid duplicate output.
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(level)

    if settings.log_format == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
        )

    root.addHandler(handler)
    _LOG_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Callers must invoke :func:`setup_logging` once at application startup
    before using loggers in production code.
    """
    return logging.getLogger(name)
