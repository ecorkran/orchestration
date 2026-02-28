"""Health check route for the daemon API."""

from __future__ import annotations

from fastapi import APIRouter, Request

from orchestration.server.models import HealthResponse

health_router = APIRouter()


@health_router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Return daemon health status and active agent count."""
    engine = request.app.state.engine
    agents = engine.list_agents()
    return HealthResponse(status="ok", agents=len(agents))
