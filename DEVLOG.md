---
docType: devlog
project: orchestration
dateCreated: 20260218
dateUpdated: 20260218
---

# Development Log

A lightweight, append-only record of development activity. Newest entries first.
Format: `## YYYYMMDD` followed by brief notes (1-3 lines per session).

---

## 20260218

### Slice 101: Anthropic Provider — Design Complete

**Documents created:**
- `user/slices/101-slice.anthropic-provider.md` — slice design

**Key design decisions:**
- **Dual auth strategy**: API key (primary, production-ready) + auth token (forward-compatible for Claude Max/OAuth). Resolution order checks config fields then Settings fields, fails explicitly if neither found.
- **Async-only client**: `AsyncAnthropic` exclusively — no sync path needed given async framework.
- **SDK streaming helper**: Uses `client.messages.stream()` context manager (not raw `stream=True`) for typed text_stream iterator and automatic cleanup.
- **Minimal error hierarchy**: `ProviderError` → `ProviderAuthError`, `ProviderAPIError`. SDK exceptions mapped to provider-level errors at boundaries.
- **No custom retry**: SDK built-in retry (2 retries, exponential backoff) is sufficient.
- **Default max_tokens=4096**: Required by Anthropic API, configurable via `ProviderConfig.extra`.

**Scope summary:**
- `AnthropicProvider` class satisfying `LLMProvider` Protocol (send_message, stream_message, validate)
- Message conversion: `orchestration.Message` → Anthropic dict format (role mapping, system extraction, consecutive role merging)
- Settings extension: `anthropic_auth_token` field (`ORCH_ANTHROPIC_AUTH_TOKEN`)
- Auto-registration in provider registry via `providers/__init__.py`
- Full mock-based test suite (no real API calls)

**Notable findings:**
- Auth token support exists in SDK (`auth_token` param on `AsyncAnthropic`), but Claude Max OAuth/PKCE token acquisition flow is not yet production-documented. Design accounts for this by treating token as pre-obtained input.

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
