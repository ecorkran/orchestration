---
docType: task-breakdown
slice: agent-registry
project: orchestration
lld: user/slices/102-slice.agent-registry.md
dependencies: [foundation, sdk-agent-provider]
projectState: Foundation complete with migration applied. SDK Agent Provider (slice 2) complete — SDKAgentProvider and SDKAgent implemented, auto-registered as "sdk", translation module working, all tests passing. The stub file core/agent_registry.py exists with a placeholder docstring. AgentConfig, AgentState, Message models in core/models.py. Agent/AgentProvider Protocols in providers/base.py. Provider registry in providers/registry.py. ProviderError hierarchy in providers/errors.py.
dateCreated: 20260219
dateUpdated: 20260219
---

## Context Summary

- Working on **Agent Registry & Lifecycle** slice — the central coordination point for agent lifecycle management
- Foundation and SDK Agent Provider slices are complete; all Protocols, models, and the SDK provider are in place
- The stub file `src/orchestration/core/agent_registry.py` exists with docstring: "Agent registry: spawn, track, and manage agent lifecycle. Populated in slice 3."
- This slice populates that stub with `AgentRegistry` class, registry errors, and a `get_registry()` singleton accessor
- Also adds `AgentInfo` and `ShutdownReport` models to `core/models.py`
- Next planned slice: **CLI Foundation & SDK Agent Tasks** (slice 4)
- **Task ordering**: test-with pattern — implementation immediately followed by tests
- **All tests use mock providers and agents** — no real SDK or API calls

### What Exists

- `src/orchestration/core/agent_registry.py` — stub with docstring only
- `src/orchestration/core/models.py` — `AgentConfig`, `AgentState`, `Message`, `MessageType`, `TopologyType`, `TopologyConfig`
- `src/orchestration/providers/base.py` — `Agent` Protocol, `AgentProvider` Protocol
- `src/orchestration/providers/registry.py` — `register_provider()`, `get_provider()`, `list_providers()`
- `src/orchestration/providers/errors.py` — `ProviderError`, `ProviderAuthError`, `ProviderAPIError`, `ProviderTimeoutError`
- `src/orchestration/providers/sdk/` — complete SDKAgentProvider and SDKAgent implementation

### What This Slice Adds

- `AgentRegistry` class with spawn, shutdown, query, and bulk shutdown
- Registry-specific errors: `AgentRegistryError`, `AgentNotFoundError`, `AgentAlreadyExistsError`
- `get_registry()` module-level singleton accessor
- `AgentInfo` and `ShutdownReport` models in `core/models.py`
- Comprehensive unit tests

---

## Tasks

### Task 1: Add AgentInfo and ShutdownReport Models
**Owner**: Junior AI
**Dependencies**: None
**Effort**: 1/5
**Objective**: Add `AgentInfo` and `ShutdownReport` Pydantic models to `src/orchestration/core/models.py`. These are read models used by the registry for agent enumeration and shutdown reporting.

**Steps**:
- [ ] Add to `src/orchestration/core/models.py`:
  ```python
  class AgentInfo(BaseModel):
      """Read model for agent enumeration — lightweight summary without Protocol access."""
      name: str
      agent_type: str
      provider: str
      state: AgentState

  class ShutdownReport(BaseModel):
      """Result of a bulk shutdown operation."""
      succeeded: list[str] = Field(default_factory=list)
      failed: dict[str, str] = Field(default_factory=dict)  # name → error message
  ```
- [ ] Verify both models are importable: `from orchestration.core.models import AgentInfo, ShutdownReport`

**Success Criteria**:
- [ ] `AgentInfo(name="a", agent_type="sdk", provider="sdk", state=AgentState.idle)` validates
- [ ] `ShutdownReport()` produces empty defaults
- [ ] `ShutdownReport(succeeded=["a"], failed={"b": "timeout"})` validates
- [ ] Existing model imports and tests are unaffected

---

### Task 2: Write AgentInfo and ShutdownReport Tests
**Owner**: Junior AI
**Dependencies**: Task 1
**Effort**: 1/5
**Objective**: Add tests for the new models to the existing model test file.

**Steps**:
- [ ] Add to `tests/test_models.py` (or `tests/core/test_models.py` — use whichever location the existing model tests are in):
  1. Test `AgentInfo` construction with all fields
  2. Test `AgentInfo` validates `state` as `AgentState` enum
  3. Test `ShutdownReport` empty defaults
  4. Test `ShutdownReport` with populated succeeded and failed fields
- [ ] Run `uv run pytest tests/test_models.py` — all tests pass (new and existing)

**Success Criteria**:
- [ ] All model tests pass
- [ ] New models have construction and validation coverage
- [ ] No regressions in existing model tests

---

### Task 3: Implement Registry Errors
**Owner**: Junior AI
**Dependencies**: None (can run parallel with Tasks 1-2)
**Effort**: 1/5
**Objective**: Add registry-specific error classes to `src/orchestration/core/agent_registry.py`. These are co-located with the registry since they're only 3 small classes.

**Steps**:
- [ ] Replace the stub content in `src/orchestration/core/agent_registry.py` with the error classes (keep the module docstring, update it):
  ```python
  """Agent registry: spawn, track, and manage agent lifecycle."""

  class AgentRegistryError(Exception):
      """Base for registry-specific errors."""

  class AgentNotFoundError(AgentRegistryError):
      """Raised when referencing a non-existent agent name."""

  class AgentAlreadyExistsError(AgentRegistryError):
      """Raised when spawning with a duplicate name."""
  ```
- [ ] Verify imports: `from orchestration.core.agent_registry import AgentRegistryError, AgentNotFoundError, AgentAlreadyExistsError`

**Success Criteria**:
- [ ] All three errors are importable
- [ ] `AgentNotFoundError` and `AgentAlreadyExistsError` are subclasses of `AgentRegistryError`
- [ ] `AgentRegistryError` is a subclass of `Exception`

---

### Task 4: Implement AgentRegistry — Core Structure and Spawn
**Owner**: Junior AI
**Dependencies**: Tasks 1, 3
**Effort**: 2/5
**Objective**: Implement the `AgentRegistry` class with the `spawn()` method and internal storage. This is the central method — it resolves a provider via the provider registry, creates an agent, and tracks it by name.

**Steps**:
- [ ] Add to `src/orchestration/core/agent_registry.py`, below the error classes:
- [ ] Import required types:
  ```python
  from orchestration.core.models import AgentConfig, AgentInfo, AgentState, ShutdownReport
  from orchestration.providers.base import Agent
  from orchestration.providers.registry import get_provider
  from orchestration.logging import get_logger
  ```
- [ ] Implement `AgentRegistry` class:
  - `__init__`: initialize `self._agents: dict[str, Agent] = {}` and `self._configs: dict[str, AgentConfig] = {}` and logger
  - `async def spawn(self, config: AgentConfig) -> Agent`:
    1. Check `config.name` not in `self._agents` — raise `AgentAlreadyExistsError` if duplicate
    2. Call `provider = get_provider(config.provider)` — `KeyError` propagates if provider unknown
    3. Call `agent = await provider.create_agent(config)` — `ProviderError` subtypes propagate
    4. Store `self._agents[config.name] = agent` and `self._configs[config.name] = config`
    5. Log `agent.spawned` at INFO level with name, agent_type, provider
    6. Return agent
- [ ] Add `has(self, name: str) -> bool` — checks if name is in `self._agents`
- [ ] Add `get(self, name: str) -> Agent`:
  - Raise `AgentNotFoundError` if name not in `self._agents`
  - Return the `Agent` instance

**Success Criteria**:
- [ ] `spawn()` creates an agent via the correct provider and stores it
- [ ] `spawn()` with duplicate name raises `AgentAlreadyExistsError`
- [ ] `spawn()` with unknown provider raises `KeyError` (from provider registry)
- [ ] `get()` returns a stored agent
- [ ] `get()` with unknown name raises `AgentNotFoundError`
- [ ] `has()` returns `True` for spawned agents, `False` otherwise

---

### Task 5: Write Spawn and Lookup Tests
**Owner**: Junior AI
**Dependencies**: Task 4
**Effort**: 2/5
**Objective**: Create `tests/core/test_agent_registry.py` with tests for spawn, get, and has operations using mock providers and agents.

**Steps**:
- [ ] Create `tests/core/` directory and `tests/core/__init__.py` if they don't exist
- [ ] Create `tests/core/test_agent_registry.py`
- [ ] Create test fixtures:
  - A `MockAgent` class satisfying the `Agent` Protocol (properties: `name`, `agent_type`, `state`; async methods: `handle_message`, `shutdown`)
  - A `MockProvider` class satisfying the `AgentProvider` Protocol (`provider_type` property, `create_agent` returns a `MockAgent`, `validate_credentials` returns True)
  - A fixture that creates a fresh `AgentRegistry` and registers a mock provider via `register_provider("mock", MockProvider())` — clean up after test (remove from registry)
- [ ] Test cases:
  1. Spawn agent — verify it's returned, `has()` returns True, `get()` returns same instance
  2. Spawn stores config — verify agent is retrievable with correct name
  3. Spawn with duplicate name — raises `AgentAlreadyExistsError`
  4. Spawn with unregistered provider — raises `KeyError`
  5. Spawn when `create_agent` raises `ProviderError` — error propagates, agent is NOT stored
  6. Get with unknown name — raises `AgentNotFoundError`
  7. Has returns False for unknown name
- [ ] Run `uv run pytest tests/core/test_agent_registry.py`

**Success Criteria**:
- [ ] All spawn and lookup tests pass
- [ ] Mock provider and agent satisfy their respective Protocols
- [ ] Error cases are verified (duplicate, unknown provider, provider failure, not found)

---

### Task 6: Implement list_agents with Filtering
**Owner**: Junior AI
**Dependencies**: Task 4
**Effort**: 1/5
**Objective**: Add `list_agents()` method to `AgentRegistry` that returns `AgentInfo` summaries with optional filtering by state and provider.

**Steps**:
- [ ] Add to `AgentRegistry`:
  ```python
  def list_agents(
      self,
      state: AgentState | None = None,
      provider: str | None = None,
  ) -> list[AgentInfo]:
  ```
  - Iterate `self._agents` items
  - For each agent, build `AgentInfo` from `agent.name`, `agent.agent_type`, `agent.state`, and `self._configs[name].provider`
  - Apply filters: if `state` is not None, include only agents with matching state; if `provider` is not None, include only agents with matching provider
  - Return the filtered list

**Success Criteria**:
- [ ] Empty registry returns empty list
- [ ] Returns correct `AgentInfo` for all spawned agents
- [ ] Filtering by state works (include matching, exclude non-matching)
- [ ] Filtering by provider works
- [ ] Both filters can be combined
- [ ] `AgentInfo.provider` comes from stored config, not from agent object

---

### Task 7: Write list_agents Tests
**Owner**: Junior AI
**Dependencies**: Tasks 5, 6
**Effort**: 1/5
**Objective**: Add tests for `list_agents` to `tests/core/test_agent_registry.py`.

**Steps**:
- [ ] Test cases (build on the mock fixtures from Task 5):
  1. Empty registry — `list_agents()` returns `[]`
  2. Two agents spawned — `list_agents()` returns two `AgentInfo` objects with correct fields
  3. Filter by state — spawn agents, set one mock agent's state to `AgentState.processing`, filter returns only matching
  4. Filter by provider — register two mock providers with different names, spawn one of each, filter returns only matching
  5. Combined filters — both state and provider filters applied together
  6. Filter with no matches — returns empty list

**Success Criteria**:
- [ ] All list_agents tests pass
- [ ] Filtering logic verified for state, provider, and combination

---

### Task 8: Implement Individual Agent Shutdown
**Owner**: Junior AI
**Dependencies**: Task 4
**Effort**: 1/5
**Objective**: Add `shutdown_agent()` method that shuts down a named agent and removes it from the registry.

**Steps**:
- [ ] Add to `AgentRegistry`:
  ```python
  async def shutdown_agent(self, name: str) -> None:
  ```
  - Look up agent by name — raise `AgentNotFoundError` if not found
  - Call `await agent.shutdown()`
  - Remove from `self._agents` and `self._configs` **regardless of whether shutdown raised** (an agent in an indeterminate state should not remain tracked)
  - Log `agent.shutdown` at INFO level
  - If `agent.shutdown()` raised, log `agent.shutdown_failed` at WARNING with error details, then re-raise the exception after removal

**Success Criteria**:
- [ ] Shutdown calls `agent.shutdown()` and removes agent from registry
- [ ] After shutdown, `has(name)` returns False and `get(name)` raises `AgentNotFoundError`
- [ ] Shutdown with unknown name raises `AgentNotFoundError`
- [ ] If `agent.shutdown()` raises, agent is still removed from registry
- [ ] If `agent.shutdown()` raises, the exception propagates to the caller

---

### Task 9: Write Individual Shutdown Tests
**Owner**: Junior AI
**Dependencies**: Tasks 5, 8
**Effort**: 1/5
**Objective**: Add shutdown tests to `tests/core/test_agent_registry.py`.

**Steps**:
- [ ] Test cases:
  1. Shutdown existing agent — `agent.shutdown()` called, agent removed from registry
  2. After shutdown, `has()` returns False and `get()` raises `AgentNotFoundError`
  3. Shutdown unknown name — raises `AgentNotFoundError`
  4. Shutdown when `agent.shutdown()` raises — agent is still removed, exception propagates
  5. Shutdown when `agent.shutdown()` raises — verify `has()` returns False after error

**Success Criteria**:
- [ ] All individual shutdown tests pass
- [ ] Both happy-path and error-path removal verified

---

### Task 10: Implement Bulk Shutdown
**Owner**: Junior AI
**Dependencies**: Task 8
**Effort**: 1/5
**Objective**: Add `shutdown_all()` method that shuts down every registered agent, collects errors, clears the registry, and returns a `ShutdownReport`.

**Steps**:
- [ ] Add to `AgentRegistry`:
  ```python
  async def shutdown_all(self) -> ShutdownReport:
  ```
  - Create a `ShutdownReport`
  - Iterate a snapshot of agent names (copy keys — avoid mutating dict during iteration)
  - For each agent: call `await agent.shutdown()` in a try/except
    - Success: add name to `report.succeeded`
    - Failure: add `name → str(error)` to `report.failed`
  - Clear `self._agents` and `self._configs`
  - Log `registry.shutdown_all` at INFO with count, succeeded, failed
  - Return the report

**Success Criteria**:
- [ ] All agents are shut down (each `shutdown()` is called)
- [ ] Registry is empty after `shutdown_all()`
- [ ] Successful shutdowns listed in `report.succeeded`
- [ ] Failed shutdowns listed in `report.failed` with error messages
- [ ] One agent's failure does not prevent other agents from being shut down

---

### Task 11: Write Bulk Shutdown Tests
**Owner**: Junior AI
**Dependencies**: Tasks 5, 10
**Effort**: 1/5
**Objective**: Add bulk shutdown tests to `tests/core/test_agent_registry.py`.

**Steps**:
- [ ] Test cases:
  1. Empty registry — `shutdown_all()` returns report with empty succeeded and failed
  2. Two agents, both succeed — both in `report.succeeded`, registry empty
  3. Two agents, one raises — succeeded has one name, failed has one name with error message, registry still empty
  4. Three agents, all fail — all in `report.failed`, registry empty
  5. After `shutdown_all()`, `list_agents()` returns `[]`

**Success Criteria**:
- [ ] All bulk shutdown tests pass
- [ ] Error collection verified — failures don't abort remaining shutdowns
- [ ] Registry is always cleared regardless of individual failures

---

### Task 12: Implement get_registry() Singleton
**Owner**: Junior AI
**Dependencies**: Task 4
**Effort**: 1/5
**Objective**: Add module-level `get_registry()` function that returns a lazily-created singleton `AgentRegistry` instance, plus a `reset_registry()` for test cleanup.

**Steps**:
- [ ] Add at module level in `src/orchestration/core/agent_registry.py`:
  ```python
  _registry: AgentRegistry | None = None

  def get_registry() -> AgentRegistry:
      """Return the shared AgentRegistry singleton, creating it on first call."""
      global _registry
      if _registry is None:
          _registry = AgentRegistry()
      return _registry

  def reset_registry() -> None:
      """Reset the singleton. Intended for test cleanup only."""
      global _registry
      _registry = None
  ```
- [ ] Export from module: ensure `get_registry`, `reset_registry` are importable from `orchestration.core.agent_registry`

**Success Criteria**:
- [ ] `get_registry()` returns same instance on repeated calls
- [ ] `reset_registry()` causes next `get_registry()` to create a new instance
- [ ] Both functions are importable

---

### Task 13: Write Singleton Tests
**Owner**: Junior AI
**Dependencies**: Tasks 5, 12
**Effort**: 1/5
**Objective**: Add tests for the singleton accessor.

**Steps**:
- [ ] Test cases (use `reset_registry()` in fixture teardown):
  1. `get_registry()` returns an `AgentRegistry` instance
  2. Two calls to `get_registry()` return the same object (`is` identity)
  3. After `reset_registry()`, next call returns a new instance (different identity)
- [ ] Ensure test cleanup calls `reset_registry()` to avoid polluting other tests

**Success Criteria**:
- [ ] All singleton tests pass
- [ ] Identity checks confirm same-instance and new-instance behavior

---

### Task 14: Full Validation Pass
**Owner**: Junior AI
**Dependencies**: All prior tasks
**Effort**: 1/5
**Objective**: Run the complete quality gate and verify the slice is complete.

**Steps**:
- [ ] Run `uv run pytest` — all tests pass (including foundation and SDK provider tests — no regressions)
- [ ] Run `uv run ruff check src/ tests/` — no linting errors
- [ ] Run `uv run ruff format --check src/ tests/` — formatting consistent
- [ ] Run type checker — zero errors
- [ ] Verify import paths:
  - `from orchestration.core.agent_registry import AgentRegistry, get_registry, reset_registry`
  - `from orchestration.core.agent_registry import AgentRegistryError, AgentNotFoundError, AgentAlreadyExistsError`
  - `from orchestration.core.models import AgentInfo, ShutdownReport`
- [ ] Verify functional flow (with mock provider):
  - `get_registry()` returns instance
  - `spawn(config)` creates and tracks agent
  - `list_agents()` returns `AgentInfo` objects
  - `shutdown_agent(name)` removes agent
  - `shutdown_all()` returns `ShutdownReport`
- [ ] Verify no regressions in existing test suites
- [ ] Verify `core/agent_registry.py` docstring is updated (no longer says "Populated in slice 3")

**Success Criteria**:
- [ ] All tests pass (new and existing)
- [ ] `ruff check` passes
- [ ] `ruff format --check` passes
- [ ] Type checking passes with zero errors
- [ ] All registry operations verified functional
- [ ] Project is ready for slice 4 (CLI Foundation & SDK Agent Tasks) to begin
