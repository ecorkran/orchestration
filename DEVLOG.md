---
docType: devlog
project: orchestration
dateCreated: 20260218
dateUpdated: 20260219
---

# Development Log

A lightweight, append-only record of development activity. Newest entries first.
Format: `## YYYYMMDD` followed by brief notes (1-3 lines per session).

---

## 20260219

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
