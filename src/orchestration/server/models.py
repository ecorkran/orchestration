"""Pydantic models for the daemon HTTP API — request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SpawnRequest(BaseModel):
    """Request body for POST /agents — spawn a new agent."""

    name: str
    agent_type: str = "sdk"
    provider: str | None = None
    model: str | None = None
    instructions: str | None = None
    base_url: str | None = None
    cwd: str | None = None
    api_key: str | None = None
    credentials: dict[str, Any] = Field(default_factory=dict)


class MessageRequest(BaseModel):
    """Request body for POST /agents/{name}/message."""

    content: str


class TaskRequest(BaseModel):
    """Request body for POST /agents/{name}/task — one-shot spawn+message."""

    name: str
    agent_type: str = "sdk"
    provider: str | None = None
    model: str | None = None
    instructions: str | None = None
    base_url: str | None = None
    cwd: str | None = None
    api_key: str | None = None
    prompt: str


class MessageOut(BaseModel):
    """Serializable message for API responses."""

    id: str
    sender: str
    content: str
    message_type: str
    timestamp: datetime
    metadata: dict[str, Any] = {}


class MessageResponse(BaseModel):
    """Response body wrapping a list of messages."""

    messages: list[MessageOut]


class AgentInfoOut(BaseModel):
    """Serializable agent info for API responses."""

    name: str
    agent_type: str
    provider: str
    state: str


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str
    agents: int


class ShutdownReportOut(BaseModel):
    """Response body for DELETE /agents (shutdown all)."""

    succeeded: list[str]
    failed: dict[str, str]


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str
