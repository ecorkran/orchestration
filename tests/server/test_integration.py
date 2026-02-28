"""Integration test: full lifecycle through ASGI transport with mock provider."""

from __future__ import annotations

import httpx


async def test_full_lifecycle(async_client: httpx.AsyncClient):
    """Spawn → message → history → shutdown → verify history retained."""
    # 1. Spawn agent
    resp = await async_client.post(
        "/agents/",
        json={
            "name": "integ-agent",
            "agent_type": "api",
            "provider": "mock",
            "model": "m",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "integ-agent"
    assert data["state"] == "idle"

    # 2. List shows the agent
    resp = await async_client.get("/agents/")
    assert resp.status_code == 200
    agents = resp.json()
    names = [a["name"] for a in agents]
    assert "integ-agent" in names

    # 3. Send message
    resp = await async_client.post(
        "/agents/integ-agent/message",
        json={"content": "hello world"},
    )
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert len(messages) >= 1
    assert messages[0]["content"] == "mock response"

    # 4. History contains both human and agent messages
    resp = await async_client.get("/agents/integ-agent/history")
    assert resp.status_code == 200
    history = resp.json()["messages"]
    assert len(history) >= 2
    assert history[0]["sender"] == "human"
    assert history[0]["content"] == "hello world"
    assert history[1]["sender"] == "integ-agent"

    # 5. Shutdown agent
    resp = await async_client.delete("/agents/integ-agent")
    assert resp.status_code == 204

    # 6. History still accessible after shutdown
    resp = await async_client.get("/agents/integ-agent/history")
    assert resp.status_code == 200
    history = resp.json()["messages"]
    assert len(history) >= 2

    # 7. Agent no longer in list
    resp = await async_client.get("/agents/")
    assert resp.status_code == 200
    agents = resp.json()
    names = [a["name"] for a in agents]
    assert "integ-agent" not in names

    # 8. Health shows 0 agents
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["agents"] == 0
