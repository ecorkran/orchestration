---
docType: slice-design
slice: foundation
project: orchestration
parent: 100-slices.orchestration-v2.md
dependencies: []
interfaces: [sdk-agent-provider, anthropic-api-provider, agent-registry, message-bus, cli-foundation]
status: complete
dateCreated: 20260218
dateUpdated: 20260219
---

# Slice Design: Project Setup & Core Models (v2)

## Overview

Initialize the orchestration project as a Python package with `uv`, establish the `src/orchestration/` package layout matching the HLD's four-layer architecture, define the Pydantic models that every subsequent slice depends on, and configure application settings and logging. This is the foundation that all other slices build upon.

### Migration Context

The original foundation slice (v1) has been fully implemented. The architecture has since evolved from an `LLMProvider`-based design (API-only agents) to a dual-provider model with `Agent` and `AgentProvider` Protocols (SDK agents + API agents). This v2 design documents the target state. A migration section at the end specifies exactly what changes are needed to bring the implemented code into alignment.

## Value

Architectural enablement. Every slice in the plan — from the SDK Agent Provider through the CLI to the REST API — depends on the project existing, the package structure being navigable, and the core data models being defined. Completing the migration means a code agent can immediately begin work on any M1 slice with correct Protocols and models.

## Technical Scope

### Included

- Project initialization with `uv` (pyproject.toml, src layout, virtual environment) ✅ done
- `src/orchestration/` package structure matching HLD layers ✅ done (needs subdirectory additions)
- Pydantic models: AgentConfig, Message, TopologyConfig ✅ partially done (rename + field changes)
- Agent and AgentProvider Protocols in providers/base.py 🔄 replaces LLMProvider
- Provider registry (dict-based, maps provider type → AgentProvider) 🔄 retype
- Shared provider error hierarchy (providers/errors.py) ➕ new
- Pydantic Settings for application configuration ✅ done (needs field additions)
- `.env.example` with documented configuration variables ✅ done (needs updates)
- Basic structured logging setup ✅ done
- `py.typed` marker ✅ done
- Test infrastructure ✅ done (tests need updates)
- `claude-agent-sdk` dependency ➕ new

### Excluded

- Any provider implementation (SDK: slice 2, Anthropic API: slice 6)
- Agent registry logic (slice 3)
- Message bus implementation (slice 5)
- CLI commands (slice 4)
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
│       │   ├── models.py        # AgentConfig, Message, TopologyConfig
│       │   ├── agent_registry.py    # Stub
│       │   ├── message_bus.py       # Stub
│       │   ├── topology.py          # Stub
│       │   └── supervisor.py        # Stub
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py          # Agent Protocol, AgentProvider Protocol
│       │   ├── registry.py      # Provider registry (lookup by type)
│       │   ├── errors.py        # Shared error hierarchy
│       │   ├── sdk/             # SDK Agent Provider (stub __init__.py)
│       │   │   └── __init__.py
│       │   └── anthropic/       # Anthropic API Provider (stub __init__.py)
│       │       └── __init__.py
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
    ├── test_config.py           # Config loading tests
    └── test_providers.py        # Provider registry + protocol tests
```

### Component Interactions

At this stage there are no runtime interactions. The foundation provides:

1. **Models** — imported by every subsequent slice (`from orchestration.core.models import AgentConfig, Message`)
2. **Config** — imported by any slice that needs credentials or settings (`from orchestration.config import Settings`)
3. **Agent/AgentProvider Protocols** — imported by provider implementations (`from orchestration.providers.base import Agent, AgentProvider`)
4. **Provider errors** — imported by all providers (`from orchestration.providers.errors import ProviderError`)
5. **Logging** — imported by any module that needs structured logging (`from orchestration.logging import get_logger`)

## Technical Decisions

### Package Manager: uv

`uv` is the project's package manager and virtual environment tool. It replaces pip/venv/poetry with a single fast tool. The project uses `uv init` with `src` layout and `uv add` for dependency management. Lock file (`uv.lock`) is committed.

### Pydantic Models

All core data types are Pydantic `BaseModel` subclasses. This gives us validation, serialization (JSON for API, message bus), and clear contracts between components.

**AgentConfig model** (was `Agent` in v1 — renamed to clarify this is configuration, not the runtime agent):
- `id`: str (UUID, generated on creation)
- `name`: str
- `agent_type`: str — "sdk" | "api" (which execution model)
- `provider`: str (provider type name, e.g. "sdk", "anthropic", "openai")
- `model`: str | None (model identifier — required for API agents, optional for SDK agents which default to whatever Claude Code uses)
- `instructions`: str (system prompt)
- `state`: AgentState enum (idle, processing, restarting, failed, terminated)
- `created_at`: datetime
- `credentials`: dict[str, Any] (provider-specific credentials — api_key, auth_token, etc.)
- `extra`: dict[str, Any] (provider-specific options — cwd, allowed_tools, permission_mode, setting_sources, etc.)

**AgentState enum:** idle, processing, restarting, failed, terminated — matching the HLD's supervision layer states.

**Message model** (unchanged from v1):
- `id`: str (UUID)
- `sender`: str (agent name, "human", or "system")
- `recipients`: list[str] (agent names, or `["all"]` for broadcast)
- `content`: str
- `message_type`: MessageType enum (chat, system, command)
- `timestamp`: datetime
- `metadata`: dict[str, Any] (extensible, for topology hints and future needs)

**TopologyConfig model** (unchanged from v1):
- `topology_type`: TopologyType enum (broadcast, filtered, hierarchical, custom)
- `config`: dict[str, Any] (topology-specific parameters)

### Agent and AgentProvider Protocols

Defined in `providers/base.py` as Python `Protocol` classes (structural typing).

**Agent Protocol** — the runtime contract for any agent, regardless of provider:

```python
class Agent(Protocol):
    """A participant that can receive and produce messages."""
    @property
    def name(self) -> str: ...

    @property
    def agent_type(self) -> str: ...    # "sdk" | "api"

    @property
    def state(self) -> AgentState: ...

    async def handle_message(self, message: Message) -> AsyncIterator[Message]: ...

    async def shutdown(self) -> None: ...
```

**AgentProvider Protocol** — creates and manages agents of a specific type:

```python
class AgentProvider(Protocol):
    """Creates and manages agents of a specific type."""
    @property
    def provider_type(self) -> str: ...    # "sdk" | "anthropic" | "openai" | ...

    async def create_agent(self, config: AgentConfig) -> Agent: ...

    async def validate_credentials(self) -> bool: ...
```

Using `Protocol` rather than ABC lets provider implementations satisfy the contract structurally without inheritance. This works particularly well with the SDK agent, which wraps an external process rather than extending a base class.

### Provider Error Hierarchy

Defined in `providers/errors.py`. Shared across all providers.

```python
class ProviderError(Exception):
    """Base error for all provider operations."""
    pass

class ProviderAuthError(ProviderError):
    """Authentication or authorization failure."""
    pass

class ProviderAPIError(ProviderError):
    """API call failure (rate limit, server error, etc.)."""
    pass

class ProviderConfigError(ProviderError):
    """Invalid or missing provider configuration."""
    pass
```

### Provider Registry

A dict-based registry in `providers/registry.py` that maps provider type names to `AgentProvider` instances or factory functions.

```python
def register_provider(provider_type: str, factory: Callable[[...], AgentProvider]) -> None: ...
def get_provider(provider_type: str) -> AgentProvider: ...
def list_providers() -> list[str]: ...
```

The registry returns `AgentProvider` instances (or factories that produce them), not `Agent` instances. Callers use the provider to create agents: `provider = get_provider("sdk"); agent = await provider.create_agent(config)`.

### Configuration: Pydantic Settings

`config.py` uses `pydantic-settings` to load from environment variables and `.env` files.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORCH_", env_file=".env")

    # Provider defaults
    default_provider: str = "sdk"           # Changed from "anthropic" — SDK agents are primary
    default_model: str = "claude-sonnet-4-20250514"

    # Anthropic API
    anthropic_api_key: str | None = None
    anthropic_auth_token: str | None = None     # NEW: bearer token auth
    anthropic_base_url: str | None = None       # NEW: proxy/gateway support

    # SDK Agent
    sdk_default_cwd: str | None = None          # NEW: default working directory for SDK agents

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"

    # Server (used by later slices)
    host: str = "127.0.0.1"
    port: int = 8000
```

All env vars prefixed with `ORCH_` (e.g., `ORCH_ANTHROPIC_API_KEY`, `ORCH_SDK_DEFAULT_CWD`).

### Logging

`logging.py` provides a `get_logger(name: str)` function that returns a configured stdlib logger. Supports two formats: JSON (for structured log aggregation) and text (for development). Configured via `Settings.log_level` and `Settings.log_format`. Unchanged from v1.

### Dependencies

pyproject.toml dependencies for the full project (installed now, used by later slices):

- `claude-agent-sdk` — **NEW**: Claude Agent SDK for SDK agents (slice 2)
- `anthropic` — Anthropic SDK for API agents (slice 6)
- `typer[all]` — CLI framework (slice 4)
- `fastapi` — REST + WebSocket API (slice 13)
- `uvicorn[standard]` — ASGI server (slice 13)
- `pydantic` — Data models (this slice)
- `pydantic-settings` — Configuration (this slice)
- `google-adk` — ADK integration (slice 11)
- `mcp` — MCP server SDK (slice 12)

Dev dependencies:
- `pytest`
- `pytest-asyncio`
- `ruff` (linting + formatting)

## Integration Points

### Provides to Other Slices

| What | Used By | Import Path |
|------|---------|-------------|
| AgentConfig, AgentState | Slices 2-16 | `orchestration.core.models` |
| Message, MessageType | Slices 5-16 | `orchestration.core.models` |
| TopologyConfig, TopologyType | Slices 5, 9 | `orchestration.core.models` |
| Agent Protocol | Slices 2, 6, 10 | `orchestration.providers.base` |
| AgentProvider Protocol | Slices 2, 6, 10 | `orchestration.providers.base` |
| Provider registry | Slices 2, 6, 10, 3 | `orchestration.providers.registry` |
| Provider errors | Slices 2, 6, 10 | `orchestration.providers.errors` |
| Settings | All slices needing config | `orchestration.config` |
| get_logger | All slices | `orchestration.logging` |
| Package structure | All slices (import paths) | Directory layout |

### Consumes from Other Slices

Nothing. This is the root of the dependency graph.

## Success Criteria

### Functional Requirements

- `uv sync` completes without errors and creates a working virtual environment
- `from orchestration.core.models import AgentConfig, Message, AgentState, MessageType` works
- `from orchestration.config import Settings` loads defaults and reads from `.env`
- `from orchestration.providers.base import Agent, AgentProvider` imports the Protocols
- `from orchestration.providers.errors import ProviderError, ProviderAuthError` works
- `from orchestration.logging import get_logger` returns a configured logger
- All stub modules are importable (e.g., `from orchestration.core import agent_registry`)
- `Settings()` with no env vars produces valid defaults (including `default_provider = "sdk"`)
- `Settings()` with `ORCH_ANTHROPIC_API_KEY=test` picks up the value
- `Settings()` with `ORCH_SDK_DEFAULT_CWD=/path` picks up the value

### Technical Requirements

- `pytest` runs and passes (model validation tests, config loading tests, protocol tests)
- `ruff check` passes with no errors
- `ruff format --check` passes (consistent formatting)
- Type checking passes

### Integration Requirements

- A subsequent slice can create a branch, add implementation to a stub module, import models and config, and run tests — with zero setup beyond `uv sync`

---

## Migration from v1

The original foundation (v1) is fully implemented. The following changes bring it to the v2 target state. These are organized as a task checklist suitable for a code agent.

### M-1: Add `claude-agent-sdk` dependency

**What:** Add `claude-agent-sdk` to pyproject.toml and run `uv sync`.

**Why:** SDK Agent Provider (slice 2) needs this package. Installing all deps up front was the original design decision.

**Files changed:** `pyproject.toml`, `uv.lock`

### M-2: Add provider subdirectories

**What:** Create `src/orchestration/providers/sdk/__init__.py` and `src/orchestration/providers/anthropic/__init__.py` as stubs with docstrings.

**Why:** The HLD now organizes providers into subdirectories. SDK Agent Provider goes in `providers/sdk/`, Anthropic API Provider goes in `providers/anthropic/`.

**Files changed:** Two new `__init__.py` files.

**Stub docstrings:**
- `providers/sdk/__init__.py`: "SDK Agent Provider — wraps claude-agent-sdk for autonomous agent execution. Populated in slice 2."
- `providers/anthropic/__init__.py`: "Anthropic API Provider — wraps anthropic SDK for conversational agent execution. Populated in slice 6."

### M-3: Rename `Agent` model to `AgentConfig`, update fields

**What:** In `core/models.py`:
1. Rename `Agent` class to `AgentConfig`
2. Add field `agent_type: str = "api"` (default keeps backward compat for API-style configs)
3. Change `model` field to `model: str | None = None` (optional — SDK agents may not specify a model)
4. Add field `credentials: dict[str, Any] = {}` (provider-specific credentials)
5. Add field `extra: dict[str, Any] = {}` (was `extra` in old `ProviderConfig` — now consolidated)
6. Remove old `ProviderConfig` model entirely (fields absorbed into `AgentConfig`)

**Why:** The architecture now distinguishes between agent configuration (this model) and the runtime agent (the Protocol). The old `Agent` name was confusing because it was a config/data model, not a live agent. `ProviderConfig` was a separate model whose fields are now part of `AgentConfig` since each agent has its own provider config.

**Files changed:** `src/orchestration/core/models.py`, `src/orchestration/core/__init__.py` (if it re-exports), `src/orchestration/__init__.py` (if it re-exports)

**Backward compatibility note:** Any code importing `Agent` from `core.models` breaks. Since no downstream slices are implemented yet, this is safe. If desired, a temporary `Agent = AgentConfig` alias can be added during transition, but it's cleaner to just rename.

### M-4: Replace `LLMProvider` Protocol with `Agent` and `AgentProvider` Protocols

**What:** In `providers/base.py`, replace the entire `LLMProvider` Protocol with:

```python
from __future__ import annotations
from collections.abc import AsyncIterator
from typing import Protocol

from orchestration.core.models import AgentConfig, AgentState, Message


class Agent(Protocol):
    """A participant that can receive and produce messages."""

    @property
    def name(self) -> str: ...

    @property
    def agent_type(self) -> str: ...

    @property
    def state(self) -> AgentState: ...

    async def handle_message(self, message: Message) -> AsyncIterator[Message]: ...

    async def shutdown(self) -> None: ...


class AgentProvider(Protocol):
    """Creates and manages agents of a specific type."""

    @property
    def provider_type(self) -> str: ...

    async def create_agent(self, config: AgentConfig) -> Agent: ...

    async def validate_credentials(self) -> bool: ...
```

**Why:** The `LLMProvider` Protocol modeled "send messages to an LLM, get text back." The new architecture has two fundamentally different agent execution models (SDK: autonomous task execution; API: conversational message exchange). The `Agent` Protocol unifies them at the interface level while the `AgentProvider` Protocol manages creation and credential validation.

**Files changed:** `src/orchestration/providers/base.py`

### M-5: Retype provider registry

**What:** In `providers/registry.py`:
1. Change the registry dict type from `dict[str, Callable[..., LLMProvider]]` to `dict[str, Callable[..., AgentProvider]]` (or keep it flexible with `Any` and document the expected type)
2. Update `get_provider` return type annotation from `LLMProvider` to `AgentProvider`
3. Update imports

**Why:** The registry now stores AgentProvider factories, not LLMProvider factories.

**Files changed:** `src/orchestration/providers/registry.py`

### M-6: Create provider error hierarchy

**What:** Create `src/orchestration/providers/errors.py` with:

```python
class ProviderError(Exception):
    """Base error for all provider operations."""
    pass

class ProviderAuthError(ProviderError):
    """Authentication or authorization failure."""
    pass

class ProviderAPIError(ProviderError):
    """API call failure (rate limit, server error, etc.)."""
    pass

class ProviderConfigError(ProviderError):
    """Invalid or missing provider configuration."""
    pass
```

**Why:** This was planned for the Anthropic provider slice (101 in v1) but belongs in foundation since all providers share it.

**Files changed:** New file `src/orchestration/providers/errors.py`

### M-7: Update Settings

**What:** In `config.py`:
1. Change `default_provider` default from `"anthropic"` to `"sdk"`
2. Add `anthropic_auth_token: str | None = None`
3. Add `anthropic_base_url: str | None = None`
4. Add `sdk_default_cwd: str | None = None`
5. Remove `anthropic_credential_path` (was for the old auth model; replaced by `anthropic_auth_token`)

**Files changed:** `src/orchestration/config.py`

### M-8: Update `.env.example`

**What:** Update the documented environment variables to reflect Settings changes. Add `ORCH_ANTHROPIC_AUTH_TOKEN`, `ORCH_ANTHROPIC_BASE_URL`, `ORCH_SDK_DEFAULT_CWD`. Remove `ORCH_ANTHROPIC_CREDENTIAL_PATH`. Update `ORCH_DEFAULT_PROVIDER` default comment to `sdk`.

**Files changed:** `.env.example`

### M-9: Update stub module docstrings

**What:** Update docstrings in stub modules to reference correct slice numbers from the revised slice plan:
- `core/agent_registry.py`: "Agent registry: spawn, track, and manage agent lifecycle. Populated in slice 3."
- `core/message_bus.py`: "Async pub/sub message bus for agent communication. Populated in slice 5."
- `core/topology.py`: "Communication topology manager. Populated in slice 9."
- `core/supervisor.py`: "Supervisor for agent health monitoring and restart strategies."
- `adk/__init__.py`: "ADK integration bridge. Populated in slice 11."
- `cli/__init__.py`: "CLI commands via Typer. Populated in slice 4."
- `server/__init__.py`: "FastAPI REST + WebSocket server. Populated in slice 13."
- `mcp/__init__.py`: "MCP server for tool exposure. Populated in slice 12."

**Files changed:** All stub modules listed above.

### M-10: Update tests

**What:**
1. `test_models.py`: Update tests for `AgentConfig` (was `Agent`). Add tests for new fields (`agent_type`, `credentials`, `extra`, optional `model`). Remove `ProviderConfig` tests (model removed). Keep Message and TopologyConfig tests unchanged.
2. `test_providers.py`: Update to test registry with `AgentProvider` type annotations. Update protocol tests to check `Agent` and `AgentProvider` Protocol shapes instead of `LLMProvider`.
3. `test_config.py`: Add tests for new Settings fields (`anthropic_auth_token`, `anthropic_base_url`, `sdk_default_cwd`). Update `default_provider` default assertion to `"sdk"`. Remove `anthropic_credential_path` test.
4. Add `test_errors.py` (or include in `test_providers.py`): Verify error hierarchy (ProviderAuthError is ProviderError, etc.).

**Files changed:** `tests/test_models.py`, `tests/test_providers.py`, `tests/test_config.py`

### M-11: Verify all success criteria

**What:** Run the full verification:
- `uv sync` succeeds
- All imports from success criteria work
- `uv run pytest` passes
- `uv run ruff check src/ tests/` passes
- `uv run ruff format --check src/ tests/` passes
- Type checking passes

### Migration Order

The migration tasks have natural dependencies:

```
M-1: Add claude-agent-sdk dependency (independent)
M-2: Add provider subdirectories (independent)
M-6: Create error hierarchy (independent)
M-3: Rename Agent → AgentConfig (independent, but do before M-4)
M-4: Replace LLMProvider with Agent/AgentProvider Protocols (after M-3)
M-5: Retype provider registry (after M-4)
M-7: Update Settings (independent)
M-8: Update .env.example (after M-7)
M-9: Update stub docstrings (independent)
M-10: Update tests (after M-3, M-4, M-5, M-6, M-7)
M-11: Verify (after all)
```

A code agent can batch M-1, M-2, M-6, M-9 as independent changes, then do M-3 → M-4 → M-5 as a chain, M-7 → M-8 as a chain, and finally M-10 → M-11.

### Risk Assessment

**Low risk overall.** No downstream code depends on the current foundation except tests. The migration is purely renaming and restructuring — no behavioral changes. The biggest risk is import path breakage if any ad-hoc scripts or notebooks reference `Agent` or `LLMProvider` by the old names, but since only the foundation slice has been implemented, this is unlikely.
