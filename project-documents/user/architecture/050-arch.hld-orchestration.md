---
docType: architecture
layer: project
project: orchestration
archIndex: 050
component: hld-orchestration
dateCreated: 20260218
dateUpdated: 20260218
status: active
---

# Orchestration — Project Overview

## What Is This?

Orchestration is a Python-based multi-agent communication and coordination system. It enables spawning AI agent instances, managing their lifecycle, and experimenting with different communication topologies — particularly peer-based patterns where agents self-select whether to engage rather than being directed by a rigid controller.

The system exposes functionality through CLI, MCP server, and REST+WebSocket API, making it accessible to humans, AI agents, and other tools.

## Technology Stack

Python 3.12+, FastAPI, Typer, Google ADK, Pydantic, asyncio. Multi-provider LLM support (Anthropic primary, OpenAI, Google). No Electron, no Node.js.

## Project History

This project reboots an earlier Node.js/TypeScript/Electron implementation. The conceptual wins from that version (peer-based communication, message bus architecture, per-agent conversation filtering, transport/logic separation) carry forward. The code does not. See the initiative HLD for details on what was retained and what was dropped.

## Document Map

### Project Level (050)
- `050-arch_hld-orchestration.md` — This document. Project overview and routing.

### Initiative: Python Reboot (100-band)
- `100-arch_hld-orchestration-v2.md` — Full High-Level Design. Four-layer architecture (Core Engine, ADK Integration, Interface Layer, Frontend), LLM provider architecture, agent process management, communication topologies, deployment model.
- `100-slices_hld-orchestration-v2.md` — Slice plan. 14 slices organized around three milestones (single-agent CLI chat → agent-to-agent conversation → human + agents).
- `100-slice_*.md` — Individual slice designs (created as work progresses).
- `100-tasks_*.md` / `10n-tasks_*.md` — Task breakdowns per slice.

### Prior Work (reference only)
Old orch-prefixed documents (128, 129, 132, 140) describe Node.js/Electron era work. They are retained as architectural decision records. No code or structure carries forward.

## Key Architectural Decisions

- **CLI-first**: CLI is the primary development and experimentation interface. Other interfaces (MCP, API) consume the same core engine.
- **Credential auth priority**: Anthropic session/credential auth (Claude Max) is the primary authentication path, implemented first. API key is fallback.
- **Multi-provider**: LLMProvider Protocol abstraction supports multiple AI providers. Agents can target different providers within the same session.
- **Supervision orthogonal to topology**: The core engine includes a supervision layer responsible for detecting agent failures and applying configurable recovery strategies. This is a separate concern from agent communication and topology — agents do not supervise each other.
- **ADK as framework, not fork**: Google ADK provides workflow primitives. Custom value-add is the communication topology layer on top.
- **Frontend deferred**: No UI in initial build. REST+WebSocket API enables a future React frontend as a thin client.

## Getting Started

```bash
# Clone and setup
cd orchestration
uv sync

# Configure credentials (Anthropic Max account)
# See .env.example or docs/

# Spawn an agent and chat
orchestration spawn --name assistant --instructions "You are a helpful assistant"
orchestration chat assistant
```

(CLI commands are illustrative — exact interface defined during slice implementation.)
