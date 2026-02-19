---
docType: slice-design
slice: foundation
project: orchestration
parent: 100-slices.orchestration-v2.md
dependencies: []
interfaces: [anthropic-provider, agent-registry, message-bus, cli-foundation]
status: complete
dateCreated: 20260218
dateUpdated: 20260219
---

# Slice Design: Project Setup & Core Models

## Overview

Initialize the orchestration project as a Python package with `uv`, establish the `src/orchestration/` package layout matching the HLD's four-layer architecture, define the Pydantic models that every subsequent slice depends on, and configure application settings and logging. This is the foundation that all other slices build upon.

## Value

Architectural enablement. Every slice in the plan — from the Anthropic provider through the CLI to the REST API — depends on the project existing, the package structure being navigable, and the core data models being defined. Completing this slice means a code agent can immediately begin work on any M1 slice with a working project skeleton, importable models, and a consistent configuration system.

## Technical Scope

### Included

- Project initialization with `uv` (pyproject.toml, src layout, virtual environment)
- `src/orchestration/` package structure matching HLD layers (core, adk, cli, server, mcp)
- Pydantic models: Agent, Message, ProviderConfig, TopologyConfig
- Pydantic Settings for application configuration (provider credentials, defaults, logging level)
- `.env.example` with documented configuration variables
- Basic structured logging setup (stdlib `logging` with JSON-capable formatter)
- `py.typed` marker for type checking support
- Minimal test infrastructure (`tests/` directory, pytest configuration, one smoke test)

### Excluded

- Any LLM provider implementation (slice 2)
- Agent registry logic (slice 3)
- Message bus implementation (slice 4)
- CLI commands (slice 5)
- Any runtime behavior — this slice produces a skeleton with models, not a running system

## Architecture

### Package Structure

```
orchestration/
├── pyproject.toml
├── README.md
├── .env.example
├── src/
│   └── orchestration/
│       ├── __init__.py          # Package version, top-level exports
│       ├── py.typed
│       ├── config.py            # Pydantic Settings, env loading
│       ├── logging.py           # Logging configuration
│       ├── core/
│       │   ├── __init__.py
│       │   ├── models.py        # Agent, Message, TopologyConfig
│       │   ├── agent_registry.py    # Stub (empty module, filled in slice 3)
│       │   ├── message_bus.py       # Stub
│       │   ├── topology.py          # Stub
│       │   └── supervisor.py        # Stub
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py          # LLMProvider Protocol definition
│       │   └── registry.py      # Provider registry (lookup by name)
│       ├── adk/
│       │   └── __init__.py      # Stub
│       ├── cli/
│       │   └── __init__.py      # Stub
│       ├── server/
│       │   └── __init__.py      # Stub
│       └── mcp/
│           └── __init__.py      # Stub
└── tests/
    ├── conftest.py
    ├── test_models.py           # Model validation tests
    └── test_config.py           # Config loading tests
```

Stub modules contain only a docstring describing their future purpose. This establishes the import paths that subsequent slices will populate — no code agent has to create directories or `__init__.py` files during later slices.

### Component Interactions

At this stage there are no runtime interactions. The foundation provides:

1. **Models** — imported by every subsequent slice (`from orchestration.core.models import Agent, Message`)
2. **Config** — imported by any slice that needs credentials or settings (`from orchestration.config import Settings`)
3. **LLMProvider Protocol** — imported by provider implementations (`from orchestration.providers.base import LLMProvider`)
4. **Logging** — imported by any module that needs structured logging (`from orchestration.logging import get_logger`)

## Technical Decisions

### Package Manager: uv

`uv` is the project's package manager and virtual environment tool. It replaces pip/venv/poetry with a single fast tool. The project uses `uv init` with `src` layout and `uv add` for dependency management. Lock file (`uv.lock`) is committed.

### Pydantic Models

All core data types are Pydantic `BaseModel` subclasses. This gives us validation, serialization (JSON for API, message bus), and clear contracts between components.

**Agent model:**
- `id`: str (UUID, generated on creation)
- `name`: str
- `instructions`: str (system prompt)
- `provider`: str (provider name, e.g. "anthropic", "openai")
- `model`: str (model identifier, e.g. "claude-sonnet-4-20250514")
- `state`: AgentState enum (idle, processing, restarting, failed, terminated)
- `created_at`: datetime

**AgentState enum:** idle, processing, restarting, failed, terminated — matching the HLD's supervision layer states.

**Message model:**
- `id`: str (UUID)
- `sender`: str (agent name, "human", or "system")
- `recipients`: list[str] (agent names, or `["all"]` for broadcast)
- `content`: str
- `message_type`: MessageType enum (chat, system, command)
- `timestamp`: datetime
- `metadata`: dict[str, Any] (extensible, for topology hints and future needs)

**ProviderConfig model:**
- `provider`: str (provider name)
- `model`: str (default model)
- `api_key`: str | None (for API key auth)
- `credential_path`: str | None (for credential/session auth)
- `extra`: dict[str, Any] (provider-specific options)

**TopologyConfig model:**
- `topology_type`: TopologyType enum (broadcast, filtered, hierarchical, custom)
- `config`: dict[str, Any] (topology-specific parameters)

### LLMProvider Protocol

Defined in `providers/base.py` as a Python `Protocol` (structural typing). This is the contract that slice 2 (Anthropic) and slice 11 (OpenAI, others) will implement.

```python
class LLMProvider(Protocol):
    async def send_message(
        self, messages: list[Message], system: str | None = None
    ) -> str: ...

    async def stream_message(
        self, messages: list[Message], system: str | None = None
    ) -> AsyncIterator[str]: ...

    async def validate(self) -> bool: ...

    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...
```

Using `Protocol` rather than ABC lets provider implementations satisfy the contract structurally without inheritance, which works better with ADK integration later.

### Provider Registry

A simple dict-based registry in `providers/registry.py` that maps provider names to factory functions. Slices that add providers register themselves. The registry provides `get_provider(name: str, config: ProviderConfig) -> LLMProvider`.

### Configuration: Pydantic Settings

`config.py` uses `pydantic-settings` to load from environment variables and `.env` files.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORCH_", env_file=".env")

    # Provider defaults
    default_provider: str = "anthropic"
    default_model: str = "claude-sonnet-4-20250514"

    # Anthropic
    anthropic_api_key: str | None = None
    anthropic_credential_path: str | None = None

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"

    # Server (used by later slices)
    host: str = "127.0.0.1"
    port: int = 8000
```

All env vars prefixed with `ORCH_` (e.g., `ORCH_ANTHROPIC_API_KEY`).

### Logging

`logging.py` provides a `get_logger(name: str)` function that returns a configured stdlib logger. Supports two formats: JSON (for structured log aggregation) and text (for development). Configured via `Settings.log_level` and `Settings.log_format`.

No third-party logging library. Stdlib `logging` with a custom JSON formatter is sufficient and avoids dependency bloat. If structlog or similar is wanted later, it can wrap this without breaking consumers.

### Dependencies

pyproject.toml dependencies for the full project (installed now, used by later slices):

- `anthropic` — Anthropic SDK (slice 2)
- `typer[all]` — CLI framework (slice 5)
- `fastapi` — REST + WebSocket API (slice 14)
- `uvicorn[standard]` — ASGI server (slice 14)
- `pydantic` — Data models (this slice)
- `pydantic-settings` — Configuration (this slice)
- `google-adk` — ADK integration (slice 12)
- `mcp` — MCP server SDK (slice 13)

Dev dependencies:
- `pytest`
- `pytest-asyncio`
- `ruff` (linting + formatting)

All dependencies are installed up front so later slices don't have to manage dependency additions — they just import and use.

## Integration Points

### Provides to Other Slices

This slice provides the foundation that every other slice imports:

| What | Used By | Import Path |
|------|---------|-------------|
| Agent, AgentState | Slices 2-16 | `orchestration.core.models` |
| Message, MessageType | Slices 4-16 | `orchestration.core.models` |
| ProviderConfig | Slices 2, 11 | `orchestration.core.models` |
| TopologyConfig, TopologyType | Slices 4, 10 | `orchestration.core.models` |
| LLMProvider Protocol | Slices 2, 11 | `orchestration.providers.base` |
| Provider registry | Slices 2, 11, 3 | `orchestration.providers.registry` |
| Settings | All slices needing config | `orchestration.config` |
| get_logger | All slices | `orchestration.logging` |
| Package structure | All slices (import paths) | Directory layout |

### Consumes from Other Slices

Nothing. This is the root of the dependency graph.

## Success Criteria

### Functional Requirements

- `uv sync` completes without errors and creates a working virtual environment
- `from orchestration.core.models import Agent, Message, AgentState, MessageType` works
- `from orchestration.config import Settings` loads defaults and reads from `.env`
- `from orchestration.providers.base import LLMProvider` imports the Protocol
- `from orchestration.logging import get_logger` returns a configured logger
- All stub modules are importable (e.g., `from orchestration.core import agent_registry`)
- `Settings()` with no env vars produces valid defaults
- `Settings()` with `ORCH_ANTHROPIC_API_KEY=test` picks up the value

### Technical Requirements

- `pytest` runs and passes (model validation tests, config loading tests)
- `ruff check` passes with no errors
- `ruff format --check` passes (consistent formatting)
- Type checking passes (`pyright` or `mypy` — agent's choice, configure in pyproject.toml)

### Integration Requirements

- A subsequent slice can create a branch, add implementation to a stub module, import models and config, and run tests — with zero setup beyond `uv sync`
