---
docType: architecture
layer: project
project: orchestration
archIndex: 100
component: orchestration
dateCreated: 20251019
dateUpdated: 20260216
status: in_progress
---

# High-Level Design: Orchestration (Python Reboot)

## Overview

Orchestration is a Python-based multi-agent communication and coordination system. It enables developers to spawn AI agent instances, manage their lifecycle, and experiment with different communication topologies — particularly peer-based patterns where agents self-select whether to engage rather than being directed by a rigid controller.

The system prioritizes experimentation with orchestration patterns and agent communication over UI polish. It exposes functionality through CLI, MCP server, and REST+WebSocket API, making it accessible to humans, AI agents, and other tools.

### Relationship to Prior Work

This document supersedes the original Electron-based HLD. The conceptual wins from the Node.js version carry forward: the peer-based communication model, the message bus architecture, per-agent conversation filtering, and the separation between transport layer and business logic (validated by the backend extraction in slice 132). What is dropped: the Electron shell, the IPC complexity, the TypeScript toolchain, and the custom ADK wrapper/fork work (slices 128, 129) now unnecessary due to ADK native Claude support.

---

## System Architecture

Four major subsystems, layered from core outward:

### 1. Core Engine

The orchestration logic itself. Agent registry (lifecycle management), message bus (pub/sub with configurable routing and per-agent filtering), and communication topology definitions. Pure Python with no framework dependencies. The portable, testable heart of the system.

The core engine includes a supervision layer responsible for detecting agent failures and applying configurable recovery strategies. This is a separate concern from agent communication and topology — agents do not supervise each other. An orthogonal Supervisor component monitors agent health and manages restarts independently of conversation flow.

The supervision layer adopts OTP/BEAM patterns as follows:
* Let it crash, then recover: implement happy path, detect failures, recover
* Configurable restart strategies: 1-1, 1-All, Rest-1
* Circuit breaker
* Recovery policies (clean slate, resume -- configurable per agent)
* Health detection
* Agent states (idle, processing, restarting, failed, terminated)

### 2. ADK Integration Layer

Adapts Google ADK orchestration primitives (ParallelAgent, SequentialAgent, workflow patterns) to work with the core engine. Uses ADK native Claude support (no custom wrapper needed). Leverages ADK battle-tested workflow patterns while the core engine handles the communication topology that ADK does not provide.

### 3. Interface Layer

Three exposure modes, all consuming the core engine:

- **CLI** (primary development interface) — typer-based commands for spawning agents, sending messages, observing conversations, running workflows. Fastest path to experimentation.
- **MCP Server** — Exposes orchestration as MCP tools so Claude Code, Cursor, and other MCP clients can create agents, send messages, and query state programmatically.
- **REST + WebSocket API** — FastAPI server for any external client. REST for lifecycle operations, WebSocket for real-time message streaming. Enables future web UI or integration with other systems.

### 4. Frontend (deferred)

A simple React UI may be added later, connecting to the FastAPI backend via HTTP + WebSocket. Not part of the initial build. When it arrives it is a thin client — all logic lives in the core engine.

### Architecture Diagram

```
+---------------------------------------------------+
|                 Interface Layer                    |
|  +-----------+  +-----------+  +---------------+  |
|  |    CLI    |  | MCP Server|  | FastAPI + WS  |  |
|  |  (typer)  |  |  (stdio)  |  |  (port 8000)  |  |
|  +-----+-----+  +-----+-----+  +-------+-------+  |
|        |              |                |            |
|        +--------------+----------------+            |
|                       |                             |
+---------------------------------------------------+
|              ADK Integration Layer                  |
|  +------------------------------------------------+ |
|  |  Workflow Patterns (Parallel, Sequential)      | |
|  |  ADK Agent <-> Core Engine Bridge              | |
|  |  Native Claude Support (ADK built-in)          | |
|  +------------------------+-----------------------+ |
|                           |                         |
+---------------------------------------------------+
|                  Core Engine                         |
|  +--------------+ +----------+ +---------------+    |
|  | Agent        | | Message  | | Topology      |    |
|  | Registry     | | Bus      | | Manager       |    |
|  | (lifecycle)  | | (pub/sub)| | (routing)     |    |
|  +--------------+ +----------+ +---------------+    |
|  +------------------------------------------------+ |
|  | Supervisor (health monitoring, restart          | |
|  |  strategies, circuit breaker, state recovery)   | |
|  +------------------------------------------------+ |
+---------------------------------------------------+
```

---

## Technology Stack Rationale

**Python 3.12+** — Primary language. Developer strongest language, ADK most mature SDK, largest AI/ML ecosystem.

**google-adk** — Agent orchestration framework. Provides ParallelAgent, SequentialAgent, Loop, LLM-driven routing, native Claude model support, MCP tool integration, and A2A protocol. Avoids reinventing workflow primitives.

**FastAPI** — Web framework for REST + WebSocket. Async-native, automatic OpenAPI docs, trivial WebSocket support, easy deployment.

**Typer** — CLI framework. Click-based but with type hints, auto-generated help, clean API. Gets a usable CLI with minimal code.

**MCP SDK** (mcp Python package) — For exposing orchestration as MCP tools. Stdio transport for Claude Code integration.

**asyncio** — Core concurrency model. Message bus, agent execution, WebSocket streaming all async. ADK is async-native.

**Pydantic** — Data validation and serialization. Shared models across CLI, API, and MCP. FastAPI uses it natively.

**No Electron, no Node.js, no TypeScript.** The previous stack existed because the project grew out of a desktop app. This reboot starts from the functionality.

---

## Data Flow

### Agent Lifecycle

CLI/MCP/API -> Core Engine (Agent Registry) -> spawn agent instance -> register with Message Bus -> agent ready

### Message Flow

Human or agent sends message -> Message Bus receives -> applies routing topology -> filters per-agent view of conversation history -> delivers to eligible agents -> agents self-select whether to respond -> responses flow back through Message Bus -> broadcast to all subscribers (CLI output, WebSocket clients, other agents)

### ADK Workflow Flow

User defines workflow (parallel, sequential, custom) -> ADK orchestrates agent execution order -> each agent step goes through Message Bus -> results aggregate per ADK pattern -> final output returned

---

## Communication Topologies

This is the project differentiator. The Message Bus supports configurable routing strategies:

**Broadcast (default)** — All agents see all messages. Simple, good for small groups.

**Filtered** — Agents see messages addressed to them, messages to all, and their own messages. Can be extended with rules (e.g. agents see all human messages regardless of addressing).

**Hierarchical** — Orchestrator agent sees everything, worker agents see only their assigned scope. Traditional boss/worker pattern, available as one option among many.

**Custom** — User-defined routing functions. Enables experimentation with novel coordination patterns.

---

## Integration Points and System Boundaries

**Claude Code SDK** — Agent execution. Each agent instance communicates with Claude via the SDK. ADK handles this natively.

**ADK** — Workflow orchestration. The core engine provides the communication layer; ADK provides the execution patterns. They compose rather than compete.

**MCP Protocol** — External tool exposure. The orchestration system appears as a set of MCP tools to any MCP-compatible client.

**Context Forge** (future) — Context assembly for agent instructions. When Context Forge MCP server is running, orchestration agents could use it to build their own context. Shared service model.

---

## Infrastructure and Deployment

**Local development** — python -m orchestration or CLI commands. No build step, no bundling.

**MCP mode** — Configured in Claude Code MCP settings. Runs as stdio process.

**Server mode** — uvicorn orchestration.server:app. Deployable to Railway, Render, Fly.io, any container host.

**No Electron, no desktop packaging.** If a desktop presence is wanted later, a system tray utility or simple launcher can start the server.

---

## Project Structure

```
orchestration/
├── pyproject.toml
├── README.md
├── src/
│   └── orchestration/
│       ├── __init__.py
│       ├── core/                  # Core Engine
│       │   ├── agent_registry.py
│       │   ├── message_bus.py
│       │   ├── topology.py
│       │   ├── supervisor.py
│       │   └── models.py         # Pydantic models
│       ├── adk/                   # ADK Integration
│       │   ├── workflows.py
│       │   └── bridge.py
│       ├── cli/                   # CLI Interface
│       │   ├── app.py            # typer app
│       │   └── commands/
│       ├── server/                # FastAPI Interface
│       │   ├── app.py
│       │   ├── routes/
│       │   └── websocket.py
│       ├── mcp/                   # MCP Server Interface
│       │   └── server.py
│       └── config.py
├── tests/
│   ├── core/
│   ├── adk/
│   ├── cli/
│   └── server/
└── docs/
```
