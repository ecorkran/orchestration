"""FastAPI application factory for the orchestration daemon."""

from __future__ import annotations

from fastapi import FastAPI

from orchestration.server.engine import OrchestrationEngine
from orchestration.server.routes.agents import agents_router
from orchestration.server.routes.health import health_router


def create_app(engine: OrchestrationEngine) -> FastAPI:
    """Create and configure the FastAPI application.

    Stores the engine on app.state for access by route handlers,
    and includes the agent and health routers.
    """
    app = FastAPI(title="Orchestration Daemon")
    app.state.engine = engine  # type: ignore[attr-defined]
    app.include_router(agents_router)
    app.include_router(health_router)
    return app
