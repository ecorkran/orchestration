"""FastAPI application factory.

Stub created during T2 (test infrastructure). Full implementation in T8.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from orchestration.server.engine import OrchestrationEngine


def create_app(engine: OrchestrationEngine) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Orchestration Daemon")
    app.state.engine = engine  # type: ignore[attr-defined]
    return app
