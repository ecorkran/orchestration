---
docType: devlog
project: orchestration
dateCreated: 20260218
dateUpdated: 20260223
---

# Development Log

A lightweight, append-only record of development activity. Newest entries first.
Format: `## YYYYMMDD` followed by brief notes (1-3 lines per session).

---

## 20260223

### Model selection support (Issue #2)

Added `--model` flag to all review commands and spawn. Model threads through the full pipeline: config key (`default_model`) → ReviewTemplate YAML field → runner → `ClaudeAgentOptions`. Precedence: CLI flag → config → template default → None (SDK default). Template defaults: `opus` for arch/tasks, `sonnet` for code. Model shown in review output panel header at all verbosity levels. 17 new tests (298 total).

**Commit:** `9eae0f7` feat: add model selection support to review and spawn commands

### Rate limit handling fix (Issue #1)

Replaced the retry-entire-session loop (3 retries, 10s delay each) with a `receive_response()` restart on the same session. The SDK's `MessageParseError` (not publicly exported) fires on `rate_limit_event` messages the CLI emits while handling API rate limits internally. Fix catches `ClaudeSDKError` (public parent) with string match, restarts the async generator on the same connected session (anyio channel survives generator death), circuit breaker at 10 retries. Eliminates ~10-20s unnecessary delay. 3 new tests (301 total).

### Post-implementation: code review findings and fixes

Ran `orchestration review code` against its own codebase. Addressed three findings from the review:

1. **`_coerce_value` guard** — added explicit `str` check and `ValueError` for unsupported types (was silently falling through)
2. **Unknown config key warnings** — `load_config` now logs warnings for unrecognized keys in TOML files (catches typos)
3. **Double template loading** — `_execute_review` now accepts `ReviewTemplate` directly instead of re-loading by name
4. **CLAUDE.md exception** — documented that public-facing docs (`docs/`, root `README.md`) are exempt from YAML frontmatter rule

Also added rate-limit retry (3 attempts, 10s delay) in runner and friendlier CLI error message.

**Deferred findings** (logged for future work):
- Duplicated `cli_runner` fixture across 6 test files → promote to root `conftest.py`
- `_resolve_verbosity` can't override config back to 0 from CLI → consider `--quiet` flag

---

## 20260222

### Slice 106: M1 Polish & Publish — Phase 7 Implementation Complete

All 22 tasks (T1-T22) implemented. 49 new tests (28 config + 12 verbosity + 6 rules + 3 cwd), 281 total project tests passing. Zero pyright/ruff errors on src/.

**Key commits:**
| Hash | Description |
|------|-------------|
| `9034843` | feat: add persistent config system with TOML storage |
| `196f03f` | feat: add config CLI commands (set, get, list, path) |
| `b002801` | feat: add verbosity levels and improve text colors |
| `b945fb4` | feat: add --rules flag, config-based cwd, and rules injection |
| `85c953e` | chore: format and fix pyright issues in slice 106 code |
| `eb44cef` | docs: add README, COMMANDS, and TEMPLATES documentation |

**What was added:**
- `config/` package: typed key definitions, TOML load/merge/persist manager, user + project config with precedence
- Config CLI: `config set/get/list/path` commands
- Verbosity levels (0/1/2) with `-v`/`-vv` flags on all review commands
- Text color improvements: bright severity badges, white headings, default foreground body text
- `--rules` flag on `review code` with config-based `default_rules`
- Config-based `--cwd` resolution across all review commands
- Documentation: `docs/README.md`, `docs/COMMANDS.md`, `docs/TEMPLATES.md`

**Architecture note:** `config.py` restructured to `config/__init__.py` package (same pattern as templates in slice 105) to coexist with `keys.py` and `manager.py`. TOML reading via stdlib `tomllib`, writing via `tomli-w`.

### Slice 106: M1 Polish & Publish — Phase 5 Task Breakdown Complete

Task file created at `project-documents/user/tasks/106-tasks.m1-polish-and-publish.md` (219 lines, 22 tasks).

**Commit:** `09a69cd` docs: add slice 106 task breakdown (m1-polish-and-publish)

### Slice 105: Review Workflow Templates — Phase 7 Implementation Complete

All 22 tasks (T1-T22) implemented. 76 review-specific tests, 226 total project tests passing. Zero pyright/ruff errors. Build succeeds.

**Key commits:**
| Hash | Description |
|------|-------------|
| `29c53e2` | feat: add pyyaml dependency |
| `dc8a4a4` | feat: add review result models |
| `fad9109` | feat: add ReviewTemplate, YAML loader, and registry |
| `1d29679` | refactor: restructure templates as package with builtin directory |
| `ea5839d` | feat: add built-in review templates (arch, tasks, code) |
| `a430358` | feat: add review result parser |
| `bff53a0` | feat: add review runner |
| `2feca18` | feat: add review CLI subcommand |
| `74eca88` | chore: review slice 105 final validation pass |

**Architecture note:** `templates.py` moved to `templates/__init__.py` package to coexist with `templates/builtin/` YAML directory. SDK literal types handled via `type: ignore` comments since template values are dynamic from YAML.

### Slice 105: Review Workflow Templates — Phase 5 Task Breakdown Complete

Task file created at `project-documents/user/tasks/105-tasks.review-workflow-templates.md` (210 lines, 22 tasks). Covers result models, YAML loader/registry, three built-in templates (arch, tasks, code), result parser, review runner, and CLI subcommand. Test-with ordering applied throughout; commit checkpoints after each stable milestone. Merge conflict in slice frontmatter resolved by PM prior to task creation.

---

## 20260220

### Slice 103: CLI Foundation & SDK Agent Tasks — Implementation Complete

**Commits:**
| Hash | Description |
|------|-------------|
| `8e76a6d` | feat: add Typer app scaffolding and pyproject.toml entry point |
| `4a4a478` | feat: implement CLI commands (spawn, list, task, shutdown) and test infra |
| `faaa5cc` | feat: refactor CLI commands to plain functions + add command tests |
| `b58d539` | feat: add integration smoke test + fix lint/type issues |

**What works:**
- 150 tests passing (22 new + 128 existing), ruff clean, pyright zero errors on src/ and tests/cli/
- `orchestration spawn --name NAME [--type sdk] [--provider P] [--cwd PATH] [--system-prompt TEXT] [--permission-mode MODE]`
- `orchestration list [--state STATE] [--provider P]` — rich table with color-coded state
- `orchestration task AGENT PROMPT` — `handle_message` async bridge, displays text and tool-use summaries
- `orchestration shutdown AGENT` / `orchestration shutdown --all` — individual and bulk with `ShutdownReport`
- `pyproject.toml` entry point registered; `orchestration --help` works
- All commands use `asyncio.run()` bridge pattern (sync Typer → async registry/agent)
- Unit tests: mocked registry via `patch_registry` fixture; integration smoke test: real registry + mock provider

**Key decisions:**
- Commands registered as plain functions via `app.command("name")(fn)` — not sub-typers. Sub-typers created nested groups (`spawn spawn --name`) rather than flat commands (`spawn --name`).
- `task` command uses `agent.handle_message(message)` (the actual Agent Protocol method), not a hypothetical `query()` method referenced in the task design
- `asyncio.run()` per command invocation — no persistent event loop, clean for CLI use
- Integration test patches the provider registry (not the agent registry) to use a mock SDK provider

**Issues logged:** None.

**Next:** Slice 5 (SDK Client Warm Pool).

---

## 20260219

### Slice 103: CLI Foundation & SDK Agent Tasks — Design and Task Breakdown Complete

**Documents created:**
- `user/slices/103-slice.cli-foundation.md` — slice design
- `user/tasks/103-tasks.cli-foundation.md` — 11 tasks, test-with pattern

**Scope:** Typer CLI with four commands (`spawn`, `list`, `task`, `shutdown`) wiring the full path from terminal through Agent Registry and SDK Agent Provider to Claude execution. Async bridge via `asyncio.run()`. Rich output formatting (tables for `list`, styled text for responses). User-friendly error handling for all known failure modes. `pyproject.toml` script entry point. Integration smoke test (spawn → list → task → shutdown). **Completes Milestone 1.**

**Next:** Phase 7 (Implementation) on slice 103.

---

### Slice 102: Agent Registry & Lifecycle — Implementation Complete

**Commits:**
| Hash | Description |
|------|-------------|
| `23747c4` | feat: add AgentRegistry core with models, errors, spawn, and lookup |
| `9a40ff3` | feat: add list_agents filtering and individual shutdown to AgentRegistry |
| `26f61b4` | feat: add bulk shutdown and singleton accessor to AgentRegistry |
| `16d2a8a` | chore: fix linting, formatting, and type errors for agent registry |
| `a045636` | docs: mark slice 102 (Agent Registry & Lifecycle) as complete |

**What works:**
- 127 tests passing (26 new + 101 existing), ruff clean, pyright zero errors on src/ and new test file
- `AgentInfo` and `ShutdownReport` Pydantic models in `core/models.py`
- `AgentRegistryError`, `AgentNotFoundError`, `AgentAlreadyExistsError` error hierarchy
- `AgentRegistry.spawn()`: resolves provider, creates agent, tracks by unique name
- `AgentRegistry.get()`, `has()`: lookup by name with proper error raising
- `AgentRegistry.list_agents()`: returns `AgentInfo` summaries with optional state/provider filtering
- `AgentRegistry.shutdown_agent()`: always-remove semantics (agent removed even if shutdown raises)
- `AgentRegistry.shutdown_all()`: best-effort bulk shutdown returning `ShutdownReport`
- `get_registry()` / `reset_registry()` singleton accessor

**Key decisions:**
- Imports moved above error class definitions (ruff E402) — error classes placed after imports, not before
- `AgentInfo.provider` sourced from stored `AgentConfig`, not from the agent object (registry owns this mapping)
- `shutdown_agent()` uses try/finally to guarantee removal regardless of shutdown errors
- `shutdown_all()` collects errors per-agent without aborting — returns structured `ShutdownReport`
- MockAgent uses `set_state()` method instead of direct `_state` access to satisfy pyright's `reportPrivateUsage`

**Issues logged:** None.

**Next:** Slice 4 (CLI Foundation & SDK Agent Tasks).

---

### Slice 102: Agent Registry & Lifecycle — Design and Task Breakdown Complete

**Documents created:**
- `user/slices/102-slice.agent-registry.md` — slice design
- `user/tasks/102-tasks.agent-registry.md` — 14 tasks, test-with pattern

**Scope:** `AgentRegistry` class in `core/agent_registry.py` — spawn, get, has, list_agents (with state/provider filtering), shutdown_agent, shutdown_all. Registry errors (`AgentRegistryError`, `AgentNotFoundError`, `AgentAlreadyExistsError`). `AgentInfo` and `ShutdownReport` models added to `core/models.py`. Module-level `get_registry()` singleton. All tests use mock providers.

**Next:** Phase 7 (Implementation) on slice 102.

---

### Slice 101: SDK Agent Provider — Complete

**Objective:** Implement the first concrete provider — `SDKAgentProvider` and `SDKAgent` wrapping `claude-agent-sdk` for one-shot and multi-turn agent execution.

**Commits:**
| Hash | Description |
|------|-------------|
| `b44914a` | feat: implement SDK message translation module with tests |
| `f7d15e0` | feat: implement SDKAgentProvider with options mapping and tests |
| `3055fcf` | feat: implement SDKAgent with query and client modes |
| `83611a5` | feat: auto-register SDK provider and add integration tests |
| `8743255` | chore: fix linting, formatting, and type errors |

**What works:**
- 96 tests passing (51 new + 45 foundation), ruff clean, pyright strict zero errors
- `translation.py`: Converts SDK message types (AssistantMessage, ToolUseBlock, ToolResultBlock, ResultMessage) to orchestration Messages
- `SDKAgentProvider`: Maps `AgentConfig` to `ClaudeAgentOptions`, defaults `permission_mode` to `"acceptEdits"`, reads mode from `credentials` dict
- `SDKAgent` query mode: One-shot via `sdk_query()`, translates and yields response messages
- `SDKAgent` client mode: Multi-turn via `ClaudeSDKClient` (create once, reuse), `shutdown()` disconnects
- Error mapping: All 5 SDK exception types → orchestration `ProviderError` hierarchy
- Auto-registration: Importing `orchestration.providers.sdk` registers `"sdk"` in the provider registry
- `validate_credentials()` returns bool without throwing

**Key decisions:**
- `translate_sdk_message` returns `list[Message]` (not `Message | None`) — `AssistantMessage` with multiple blocks produces multiple Messages, empty list for unknown types
- Deferred import of `SDKAgent` in `provider.py` to avoid stub-state issues at module load
- ruff requires `query as sdk_query` alias in a separate import block from other `claude_agent_sdk` imports (isort rule)
- Used `__import__("claude_agent_sdk")` in `validate_credentials` to satisfy pyright's `reportUnusedImport`
- Real SDK dataclasses used for test fixtures (no MagicMock — `TextBlock`, `AssistantMessage`, etc. are simple dataclasses)

**Issues logged:** None.

**Next:** Slice 3 (Agent Registry & Lifecycle) or slice 4 (CLI Foundation).

---

### Slice 100: Foundation Migration — Complete

**Objective:** Migrate foundation from v1 (LLMProvider-based) to v2 (dual-provider Agent/AgentProvider architecture) per `100-arch.orchestration-v2.md`.

**Commits:**
| Hash | Description |
|------|-------------|
| `7200b4e` | feat: add claude-agent-sdk dependency |
| `b6e1264` | feat: add SDK and Anthropic provider subdirectories with stubs |
| `6a389a5` | feat: add shared provider error hierarchy |
| `9700bed` | refactor: rename Agent to AgentConfig, remove ProviderConfig |
| `5ebf6cb` | test: update model tests for AgentConfig migration |
| `2433494` | refactor: replace LLMProvider with Agent and AgentProvider Protocols |
| `0b4302e` | refactor: retype provider registry for AgentProvider instances |
| `90dd38b` | test: update provider tests for AgentProvider instances and error hierarchy |
| `cb1d56c` | refactor: update Settings for dual-provider architecture |
| `0d3da45` | test: update config tests for new Settings fields |
| `f944f02` | docs: update .env.example for dual-provider architecture |
| `fd45a0d` | docs: update stub docstrings with correct slice numbers |
| `f189dc2` | fix: type checking — zero pyright errors |
| `5aaf718` | docs: mark foundation migration tasks and slice complete |

**What works:**
- 45 tests passing, ruff check clean, ruff format clean, pyright strict zero errors
- `AgentConfig` model with SDK-specific fields (cwd, setting_sources, allowed_tools, permission_mode) and API fields (model, api_key, auth_token, base_url)
- `Agent` and `AgentProvider` Protocols (runtime_checkable, structural typing)
- Provider registry maps type names to `AgentProvider` instances
- Shared error hierarchy: `ProviderError` → `ProviderAuthError`, `ProviderAPIError`, `ProviderTimeoutError`
- Settings with `default_provider="sdk"`, `default_agent_type="sdk"`, auth token and base URL support
- Provider subdirectories: `providers/sdk/` and `providers/anthropic/` with stubs
- All stub docstrings updated to correct slice numbers per v2 plan

**Key decisions:**
- `handle_message` in Agent Protocol is a sync method signature (not `async def`) — implementations are async generators, callers use `async for` directly without `await`
- `ProviderTimeoutError` chosen over `ProviderConfigError` — config errors caught at Pydantic validation time; timeout is the real operational concern
- `sdk_default_cwd` kept off Settings (per-agent config via AgentConfig, not global)
- `claude-agent-sdk` imports as `claude_agent_sdk` (module name differs from package name)

**Issues logged:** None.

**Next:** Slice 2 (SDK Agent Provider) or slice 101 (Anthropic Provider) — both can proceed in parallel as they only depend on foundation.

---

## 20260218

### Slice 101: Anthropic Provider — Design Complete

**Documents created:**
- `user/slices/101-slice.anthropic-provider.md` — slice design

**Key design decisions:**
- **API key auth only**: The official Anthropic Python SDK supports `api_key` / `ANTHROPIC_API_KEY` exclusively. No native `auth_token` parameter exists. Claude Max / OAuth bearer token usage requires external gateways (e.g., LiteLLM) — out of scope for this slice but extensible via `ProviderConfig.extra["base_url"]` in future.
- **Async-only client**: `AsyncAnthropic` exclusively — no sync path needed given async framework.
- **SDK streaming helper**: Uses `client.messages.stream()` context manager (not raw `stream=True`) for typed text_stream iterator and automatic cleanup.
- **Minimal error hierarchy**: `ProviderError` → `ProviderAuthError`, `ProviderAPIError`. SDK exceptions mapped to provider-level errors at boundaries.
- **No custom retry**: SDK built-in retry (2 retries, exponential backoff) is sufficient.
- **Default max_tokens=4096**: Required by Anthropic API, configurable via `ProviderConfig.extra`.

**Scope summary:**
- `AnthropicProvider` class satisfying `LLMProvider` Protocol (send_message, stream_message, validate)
- Message conversion: `orchestration.Message` → Anthropic dict format (role mapping, system extraction, consecutive role merging)
- API key resolution: `ProviderConfig.api_key` → `Settings.anthropic_api_key` → explicit error
- Auto-registration in provider registry via `providers/__init__.py`
- Full mock-based test suite (no real API calls)

**Commits:**
- `3c418e0` docs: add slice 101 design (Anthropic Provider)

**Next:** Phase 5 (Task Breakdown) on slice 101, then Phase 7 (Implementation).

### Slice 100: Foundation — Design and Task Creation Complete

**Documents created:**
- `user/slices/100-slice.foundation.md` — slice design (project setup, package structure, core Pydantic models, config, logging, provider protocol, test infrastructure)
- `user/tasks/100-tasks.foundation.md` — 19 granular tasks, sequentially ordered

**Key design decisions:**
- **Test-with ordering**: Tasks are structured so each implementation unit (models, providers, config, logging) is immediately followed by its tests, catching contract issues early rather than batching tests at the end
- **All dependencies installed up front**: `pyproject.toml` includes all project dependencies (anthropic, typer, fastapi, google-adk, mcp, etc.) so later slices just import and use
- **Protocol over ABC**: `LLMProvider` defined as a `Protocol` for structural typing, better ADK compatibility later
- **Stdlib logging only**: No third-party logging library; JSON formatter on stdlib `logging` keeps dependencies minimal

**Scope summary:**
- Project init with `uv`, `src/orchestration/` package layout matching HLD 4-layer architecture
- Pydantic models: Agent, Message, ProviderConfig, TopologyConfig (with StrEnum types)
- Pydantic Settings for env-based config (`ORCH_` prefix), `.env.example`
- LLMProvider Protocol + dict-based provider registry
- Structured logging (JSON + text formats)
- Full test infrastructure and validation pass

**Commits:**
- `007b02f` planning: slice 100 foundation — design and task breakdown complete

**Next:** Phase 6 (Task Expansion) on `100-tasks.foundation.md`, or proceed directly to Phase 7 (implementation) if PM approves skipping expansion for this low-complexity slice.
