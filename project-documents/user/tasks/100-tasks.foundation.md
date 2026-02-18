---
docType: task-breakdown
slice: foundation
project: orchestration
lld: user/slices/100-slice.foundation.md
dependencies: []
projectState: New Python project, no code exists yet. This is the first slice to be implemented.
dateCreated: 20260218
dateUpdated: 20260218
---

## Context Summary

- Working on the **foundation** slice — project initialization and core models
- No prior code exists; this is a greenfield Python project
- This slice produces the project skeleton, package structure, Pydantic models, configuration, logging, provider protocol, and test infrastructure
- Every subsequent slice (Anthropic provider, agent registry, message bus, CLI, etc.) depends on this foundation
- Next planned slice: Anthropic Provider with Credential Auth (slice 2)
- Package manager: `uv`
- Key dependencies: pydantic, pydantic-settings, anthropic, typer, fastapi, uvicorn, google-adk, mcp
- Dev dependencies: pytest, pytest-asyncio, ruff
- **Task ordering**: test-with pattern — each implementation unit is immediately followed by its tests so issues are caught before the next unit begins

---

## Tasks

### Task 1: Initialize Python Project with uv
**Owner**: Junior AI
**Dependencies**: None
**Effort**: 1/5
**Objective**: Create the Python project using `uv` with src layout, configure pyproject.toml with all dependencies, and verify the virtual environment works.

**Steps**:
- [ ] Run `uv init` with src layout in the project root to create the Python project structure
- [ ] Configure `pyproject.toml`:
  - Set project name to `orchestration`
  - Set Python version requirement to `>=3.12`
  - Add production dependencies: `pydantic`, `pydantic-settings`, `anthropic`, `typer[all]`, `fastapi`, `uvicorn[standard]`, `google-adk`, `mcp`
  - Add dev dependencies: `pytest`, `pytest-asyncio`, `ruff`
  - Configure ruff settings (line-length = 88)
  - Configure pytest settings (asyncio_mode = "auto")
- [ ] Run `uv sync` to install all dependencies and create the lock file
- [ ] Commit `uv.lock` to source control

**Success Criteria**:
- [ ] `pyproject.toml` exists with all specified dependencies
- [ ] `uv sync` completes without errors
- [ ] `uv.lock` is generated and committed
- [ ] Virtual environment is created and functional

---

### Task 2: Create Package Directory Structure
**Owner**: Junior AI
**Dependencies**: Task 1
**Effort**: 1/5
**Objective**: Create the full `src/orchestration/` package layout with all sub-packages and stub modules matching the HLD's layer architecture.

**Steps**:
- [ ] Create `src/orchestration/__init__.py` with package version and top-level exports
- [ ] Create `src/orchestration/py.typed` (empty marker file for type checking)
- [ ] Create `src/orchestration/core/__init__.py`
- [ ] Create `src/orchestration/core/agent_registry.py` — stub with docstring: "Agent registry: spawn, track, and manage agent lifecycle. Populated in slice 3."
- [ ] Create `src/orchestration/core/message_bus.py` — stub with docstring: "Async pub/sub message bus for agent communication. Populated in slice 4."
- [ ] Create `src/orchestration/core/topology.py` — stub with docstring: "Communication topology manager. Populated in slice 10."
- [ ] Create `src/orchestration/core/supervisor.py` — stub with docstring: "Supervisor for agent health monitoring and restart strategies. Populated in slice 6."
- [ ] Create `src/orchestration/providers/__init__.py`
- [ ] Create `src/orchestration/adk/__init__.py` — stub with docstring: "ADK integration bridge. Populated in slice 12."
- [ ] Create `src/orchestration/cli/__init__.py` — stub with docstring: "CLI commands via Typer. Populated in slice 5."
- [ ] Create `src/orchestration/server/__init__.py` — stub with docstring: "FastAPI REST + WebSocket server. Populated in slice 14."
- [ ] Create `src/orchestration/mcp/__init__.py` — stub with docstring: "MCP server for tool exposure. Populated in slice 13."

**Success Criteria**:
- [ ] All directories and `__init__.py` files exist per the package structure in the slice design
- [ ] Every stub module contains a descriptive docstring of its future purpose
- [ ] `py.typed` marker file exists
- [ ] All stub modules are importable (e.g., `from orchestration.core import agent_registry` succeeds)

---

### Task 3: Set Up Test Infrastructure
**Owner**: Junior AI
**Dependencies**: Task 2
**Effort**: 1/5
**Objective**: Create the `tests/` directory with `conftest.py` and pytest configuration so tests are available before any implementation begins.

**Steps**:
- [ ] Create `tests/__init__.py` (if needed for imports)
- [ ] Create `tests/conftest.py` with any shared fixtures (e.g., a `Settings` fixture with test defaults)
- [ ] Verify pytest discovers and runs from the project root via `uv run pytest`

**Success Criteria**:
- [ ] `tests/conftest.py` exists with at least one shared fixture
- [ ] `uv run pytest` runs successfully (even with zero tests, it should not error)

---

### Task 4: Implement Core Pydantic Models — Enums
**Owner**: Junior AI
**Dependencies**: Task 3
**Effort**: 1/5
**Objective**: Define the `AgentState`, `MessageType`, and `TopologyType` enums in `src/orchestration/core/models.py`.

**Steps**:
- [ ] Create `src/orchestration/core/models.py`
- [ ] Add `from __future__ import annotations` at top
- [ ] Define `AgentState(StrEnum)` with values: `idle`, `processing`, `restarting`, `failed`, `terminated`
- [ ] Define `MessageType(StrEnum)` with values: `chat`, `system`, `command`
- [ ] Define `TopologyType(StrEnum)` with values: `broadcast`, `filtered`, `hierarchical`, `custom`

**Success Criteria**:
- [ ] All three enums are defined as `StrEnum` subclasses
- [ ] `from orchestration.core.models import AgentState, MessageType, TopologyType` works
- [ ] Enum values match the slice design specification exactly

---

### Task 5: Implement Core Pydantic Models — Agent
**Owner**: Junior AI
**Dependencies**: Task 4
**Effort**: 1/5
**Objective**: Define the `Agent` Pydantic model in `src/orchestration/core/models.py`.

**Steps**:
- [ ] Add the `Agent` model to `models.py` as a `BaseModel` subclass
- [ ] Fields:
  - `id`: `str` — default factory generates UUID via `uuid4()`
  - `name`: `str`
  - `instructions`: `str` (system prompt)
  - `provider`: `str` (provider name, e.g. "anthropic")
  - `model`: `str` (model identifier)
  - `state`: `AgentState` — default `AgentState.idle`
  - `created_at`: `datetime` — default factory `datetime.now(UTC)`

**Success Criteria**:
- [ ] `Agent` model validates correctly with required fields (`name`, `instructions`, `provider`, `model`)
- [ ] `id` is auto-generated as a UUID string when not provided
- [ ] `state` defaults to `idle`
- [ ] `created_at` defaults to current UTC time
- [ ] Invalid `state` values are rejected by Pydantic validation

---

### Task 6: Implement Core Pydantic Models — Message
**Owner**: Junior AI
**Dependencies**: Task 4
**Effort**: 1/5
**Objective**: Define the `Message` Pydantic model in `src/orchestration/core/models.py`.

**Steps**:
- [ ] Add the `Message` model to `models.py` as a `BaseModel` subclass
- [ ] Fields:
  - `id`: `str` — default factory generates UUID
  - `sender`: `str` (agent name, "human", or "system")
  - `recipients`: `list[str]` (agent names, or `["all"]` for broadcast)
  - `content`: `str`
  - `message_type`: `MessageType` — default `MessageType.chat`
  - `timestamp`: `datetime` — default factory `datetime.now(UTC)`
  - `metadata`: `dict[str, Any]` — default empty dict

**Success Criteria**:
- [ ] `Message` model validates correctly with required fields (`sender`, `recipients`, `content`)
- [ ] `id` and `timestamp` are auto-generated when not provided
- [ ] `message_type` defaults to `chat`
- [ ] `metadata` defaults to empty dict
- [ ] Invalid `message_type` values are rejected

---

### Task 7: Implement Core Pydantic Models — ProviderConfig
**Owner**: Junior AI
**Dependencies**: Task 4
**Effort**: 1/5
**Objective**: Define the `ProviderConfig` Pydantic model in `src/orchestration/core/models.py`.

**Steps**:
- [ ] Add the `ProviderConfig` model to `models.py`
- [ ] Fields:
  - `provider`: `str` (provider name)
  - `model`: `str` (default model)
  - `api_key`: `str | None` — default `None`
  - `credential_path`: `str | None` — default `None`
  - `extra`: `dict[str, Any]` — default empty dict

**Success Criteria**:
- [ ] `ProviderConfig` validates with required fields (`provider`, `model`)
- [ ] Optional fields default to `None` or empty dict as specified
- [ ] Model serializes to JSON correctly

---

### Task 8: Implement Core Pydantic Models — TopologyConfig
**Owner**: Junior AI
**Dependencies**: Task 4
**Effort**: 1/5
**Objective**: Define the `TopologyConfig` Pydantic model in `src/orchestration/core/models.py`.

**Steps**:
- [ ] Add the `TopologyConfig` model to `models.py`
- [ ] Fields:
  - `topology_type`: `TopologyType` — default `TopologyType.broadcast`
  - `config`: `dict[str, Any]` — default empty dict

**Success Criteria**:
- [ ] `TopologyConfig` validates correctly
- [ ] `topology_type` defaults to `broadcast`
- [ ] `config` defaults to empty dict

---

### Task 9: Write Model Validation Tests
**Owner**: Junior AI
**Dependencies**: Tasks 5, 6, 7, 8
**Effort**: 2/5
**Objective**: Create `tests/test_models.py` with tests for all Pydantic models and enums. This validates the core contracts before building anything on top of them.

**Steps**:
- [ ] Test `AgentState` enum values
- [ ] Test `MessageType` enum values
- [ ] Test `TopologyType` enum values
- [ ] Test `Agent` creation with required fields, auto-generated `id`, default `state`, default `created_at`
- [ ] Test `Agent` rejects invalid `state` values
- [ ] Test `Message` creation with required fields, auto-generated `id` and `timestamp`, default `message_type`, default `metadata`
- [ ] Test `Message` rejects invalid `message_type`
- [ ] Test `ProviderConfig` creation with required and optional fields
- [ ] Test `TopologyConfig` default values
- [ ] Test JSON serialization/deserialization round-trip for each model

**Success Criteria**:
- [ ] All model tests pass via `uv run pytest tests/test_models.py`
- [ ] Tests cover all models and enums defined in the slice design
- [ ] Edge cases (missing required fields, invalid enum values) are tested

---

### Task 10: Define LLMProvider Protocol
**Owner**: Junior AI
**Dependencies**: Task 9
**Effort**: 1/5
**Objective**: Define the `LLMProvider` Protocol in `src/orchestration/providers/base.py` as the contract for all LLM provider implementations.

**Steps**:
- [ ] Create `src/orchestration/providers/base.py`
- [ ] Import `Protocol` from `typing`, `AsyncIterator` from `collections.abc`
- [ ] Import `Message` from `orchestration.core.models`
- [ ] Define `LLMProvider(Protocol)` with:
  - `async def send_message(self, messages: list[Message], system: str | None = None) -> str`
  - `async def stream_message(self, messages: list[Message], system: str | None = None) -> AsyncIterator[str]`
  - `async def validate(self) -> bool`
  - `@property name(self) -> str`
  - `@property model(self) -> str`

**Success Criteria**:
- [ ] `from orchestration.providers.base import LLMProvider` works
- [ ] `LLMProvider` is a `Protocol` class (structural typing, not ABC)
- [ ] All method signatures match the slice design specification

---

### Task 11: Implement Provider Registry
**Owner**: Junior AI
**Dependencies**: Task 10
**Effort**: 1/5
**Objective**: Create a dict-based provider registry in `src/orchestration/providers/registry.py` that maps provider names to factory functions.

**Steps**:
- [ ] Create `src/orchestration/providers/registry.py`
- [ ] Define a module-level registry dict mapping `str` to factory callables
- [ ] Implement `register_provider(name: str, factory: Callable)` — registers a factory function for a provider name
- [ ] Implement `get_provider(name: str, config: ProviderConfig) -> LLMProvider` — looks up the factory by name, calls it with config, returns the provider instance. Raises a clear error if the name is not registered.
- [ ] Implement `list_providers() -> list[str]` — returns registered provider names

**Success Criteria**:
- [ ] `register_provider` adds a factory to the registry
- [ ] `get_provider` retrieves and invokes the correct factory
- [ ] `get_provider` raises `KeyError` (or similar clear error) for unregistered names
- [ ] `list_providers` returns the list of registered names

---

### Task 12: Write Provider Registry Tests
**Owner**: Junior AI
**Dependencies**: Task 11
**Effort**: 1/5
**Objective**: Create `tests/test_providers.py` with tests for the provider registry. Validates the registry before config and logging build on it.

**Steps**:
- [ ] Test `register_provider` adds a factory to the registry
- [ ] Test `get_provider` invokes the correct factory with the given config
- [ ] Test `get_provider` raises an error for unregistered provider names
- [ ] Test `list_providers` returns registered names

**Success Criteria**:
- [ ] All provider registry tests pass via `uv run pytest tests/test_providers.py`
- [ ] Tests verify registration, lookup, and error handling

---

### Task 13: Implement Application Configuration (Pydantic Settings)
**Owner**: Junior AI
**Dependencies**: Task 12
**Effort**: 1/5
**Objective**: Create `src/orchestration/config.py` with a `Settings` class using `pydantic-settings` for environment-based configuration.

**Steps**:
- [ ] Create `src/orchestration/config.py`
- [ ] Define `Settings(BaseSettings)` with `SettingsConfigDict(env_prefix="ORCH_", env_file=".env")`
- [ ] Fields:
  - `default_provider`: `str` = `"anthropic"`
  - `default_model`: `str` = `"claude-sonnet-4-20250514"`
  - `anthropic_api_key`: `str | None` = `None`
  - `anthropic_credential_path`: `str | None` = `None`
  - `log_level`: `str` = `"INFO"`
  - `log_format`: `str` = `"json"`
  - `host`: `str` = `"127.0.0.1"`
  - `port`: `int` = `8000`

**Success Criteria**:
- [ ] `from orchestration.config import Settings` works
- [ ] `Settings()` with no env vars produces valid defaults for all fields
- [ ] `Settings()` with `ORCH_ANTHROPIC_API_KEY=test` picks up the value
- [ ] `Settings()` reads from `.env` file when present
- [ ] All env vars are prefixed with `ORCH_`

---

### Task 14: Write Configuration Tests
**Owner**: Junior AI
**Dependencies**: Task 13
**Effort**: 1/5
**Objective**: Create `tests/test_config.py` with tests for Settings loading behavior. Validates config before logging depends on it.

**Steps**:
- [ ] Test `Settings()` produces valid defaults for all fields
- [ ] Test that setting `ORCH_ANTHROPIC_API_KEY` env var is picked up
- [ ] Test that `ORCH_LOG_LEVEL` and `ORCH_LOG_FORMAT` are respected
- [ ] Test that `ORCH_PORT` is parsed as an integer

**Success Criteria**:
- [ ] All config tests pass via `uv run pytest tests/test_config.py`
- [ ] Tests verify default values and env var overrides

---

### Task 15: Create .env.example
**Owner**: Junior AI
**Dependencies**: Task 13
**Effort**: 1/5
**Objective**: Create a documented `.env.example` file showing all configurable environment variables.

**Steps**:
- [ ] Create `.env.example` in the project root
- [ ] Document every `Settings` field with its `ORCH_`-prefixed env var name, a comment describing the purpose, and the default value
- [ ] Include section headers for logical grouping (Provider Defaults, Anthropic, Logging, Server)

**Success Criteria**:
- [ ] `.env.example` exists with all config variables documented
- [ ] Every variable uses the `ORCH_` prefix
- [ ] Comments describe purpose and default values

---

### Task 16: Implement Structured Logging
**Owner**: Junior AI
**Dependencies**: Task 14
**Effort**: 2/5
**Objective**: Create `src/orchestration/logging.py` with a `get_logger` function that returns configured stdlib loggers with JSON and text format support.

**Steps**:
- [ ] Create `src/orchestration/logging.py`
- [ ] Implement a JSON formatter class that outputs structured JSON log lines (timestamp, level, name, message)
- [ ] Implement `setup_logging(settings: Settings)` to configure the root logger based on `Settings.log_level` and `Settings.log_format`
- [ ] Implement `get_logger(name: str) -> logging.Logger` that returns a named logger
- [ ] `log_format = "json"` uses the JSON formatter; `log_format = "text"` uses standard text formatting

**Success Criteria**:
- [ ] `from orchestration.logging import get_logger` returns a configured logger
- [ ] JSON format produces valid JSON log lines
- [ ] Text format produces human-readable log lines
- [ ] Log level is configurable via `Settings.log_level`

---

### Task 17: Write Logging Tests
**Owner**: Junior AI
**Dependencies**: Task 16
**Effort**: 1/5
**Objective**: Create `tests/test_logging.py` with tests for the logging configuration. Validates logging before the final quality gate.

**Steps**:
- [ ] Test `get_logger` returns a `logging.Logger` instance
- [ ] Test JSON formatter produces valid JSON output
- [ ] Test text format produces readable output
- [ ] Test log level configuration is respected

**Success Criteria**:
- [ ] All logging tests pass via `uv run pytest tests/test_logging.py`
- [ ] Both JSON and text formats are verified

---

### Task 18: Configure Type Checking
**Owner**: Junior AI
**Dependencies**: Task 17
**Effort**: 1/5
**Objective**: Configure type checking (pyright or mypy) in `pyproject.toml` and add the type checker as a dev dependency.

**Steps**:
- [ ] Choose pyright or mypy and add it as a dev dependency via `uv add --dev`
- [ ] Add type checker configuration to `pyproject.toml` (strict mode)
- [ ] Run the type checker against the source and fix any issues

**Success Criteria**:
- [ ] Type checker is configured in `pyproject.toml`
- [ ] Type checking passes with zero errors on all source files

---

### Task 19: Full Validation Pass
**Owner**: Junior AI
**Dependencies**: All prior tasks
**Effort**: 1/5
**Objective**: Run the complete quality gate — all tests, linting, formatting, and type checking — and fix any issues.

**Steps**:
- [ ] Run `uv run pytest` — all tests pass
- [ ] Run `uv run ruff check src/ tests/` — no linting errors
- [ ] Run `uv run ruff format --check src/ tests/` — formatting is consistent
- [ ] Run type checker (pyright or mypy) — zero errors
- [ ] Verify all imports from the slice design's success criteria work:
  - `from orchestration.core.models import Agent, Message, AgentState, MessageType`
  - `from orchestration.config import Settings`
  - `from orchestration.providers.base import LLMProvider`
  - `from orchestration.logging import get_logger`
  - `from orchestration.core import agent_registry`

**Success Criteria**:
- [ ] All tests pass
- [ ] `ruff check` passes with no errors
- [ ] `ruff format --check` passes
- [ ] Type checking passes with zero errors
- [ ] All import paths from the slice design are verified working
- [ ] Project is ready for slice 2 (Anthropic Provider) to begin
