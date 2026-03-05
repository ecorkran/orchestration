"""FastAPI application factory for the squadron daemon."""

from __future__ import annotations

from fastapi import FastAPI

from squadron.server.engine import SquadronEngine
from squadron.server.routes.agents import agents_router
from squadron.server.routes.health import health_router


def create_app(engine: SquadronEngine) -> FastAPI:
    """Create and configure the FastAPI application.

    Stores the engine on app.state for access by route handlers,
    and includes the agent and health routers.
    """
    app = FastAPI(title="Orchestration Daemon")
    app.state.engine = engine  # type: ignore[attr-defined]
    app.include_router(agents_router)
    app.include_router(health_router)
    return app
