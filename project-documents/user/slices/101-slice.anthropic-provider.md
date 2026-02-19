---
docType: slice-design
slice: anthropic-provider
project: orchestration
parent: user/architecture/100-slices.orchestration-v2.md
dependencies: [foundation]
interfaces: [agent-registry, cli-foundation, additional-llm-providers]
status: not started
dateCreated: 20260218
dateUpdated: 20260218
---

# Slice Design: Anthropic Provider with Credential Auth

## Overview

Implement a concrete `AnthropicProvider` class that satisfies the `LLMProvider` Protocol established in the foundation slice. This is the first real provider — it connects the orchestration framework to the Anthropic Messages API, enabling agents to send and receive LLM completions. The provider supports two authentication strategies: API key (standard) and bearer token / auth token (for Claude Max / OAuth flows), with API key as the primary working path and auth token as a forward-compatible secondary path.

## Value

Architectural enablement and direct M1 milestone dependency. Without a working LLM provider, no agent can generate responses — the Agent Registry (slice 102), CLI (slice 104), and every downstream slice that touches LLM output are blocked. This slice transforms the orchestration skeleton into a system that can actually call Claude.

## Technical Scope

### Included

- `AnthropicProvider` class implementing the full `LLMProvider` Protocol
- API key authentication via `ProviderConfig.api_key` or `ORCH_ANTHROPIC_API_KEY`
- Auth token authentication via `ProviderConfig.extra["auth_token"]` or `ORCH_ANTHROPIC_AUTH_TOKEN`
- Non-streaming message send (`send_message`)
- Streaming message send (`stream_message`) using the SDK's async streaming helper
- Credential validation (`validate`) that makes a lightweight API call
- Message format conversion: `orchestration.core.models.Message` to/from Anthropic SDK message dicts
- Provider self-registration with the provider registry
- Settings extension: add `anthropic_auth_token` field to `Settings`
- Structured logging for API calls, auth events, and errors
- Comprehensive test suite using mocked SDK calls

### Excluded

- Claude Max OAuth/PKCE flow implementation (auth token assumed to be pre-obtained; the mechanism to acquire tokens is outside this slice's scope)
- Other LLM providers (slice 110)
- Agent lifecycle management (slice 102)
- CLI commands (slice 104)
- Retry/backoff beyond what the Anthropic SDK provides natively (SDK has built-in retry with `max_retries=2`)
- Tool use / function calling support (can be added in a future slice when needed)
- Extended thinking support (deferred)

## Dependencies

### Prerequisites

- **Foundation (slice 100)**: Complete. Provides `LLMProvider` Protocol, `ProviderConfig`, `Message`, provider registry, `Settings`, and `get_logger`.
- **Anthropic Python SDK** (`anthropic>=0.40.0`): Already in `pyproject.toml`. Provides `AsyncAnthropic` client, streaming helpers, and typed error hierarchy.

### Interfaces Required

| Interface | Source | Import Path |
|-----------|--------|-------------|
| LLMProvider Protocol | Foundation | `orchestration.providers.base` |
| ProviderConfig | Foundation | `orchestration.core.models` |
| Message | Foundation | `orchestration.core.models` |
| register_provider | Foundation | `orchestration.providers.registry` |
| Settings | Foundation | `orchestration.config` |
| get_logger | Foundation | `orchestration.logging` |

## Architecture

### Component Structure

```
src/orchestration/
├── providers/
│   ├── __init__.py          # Updated: import and register AnthropicProvider
│   ├── base.py              # Unchanged: LLMProvider Protocol
│   ├── registry.py          # Unchanged: provider registry
│   └── anthropic.py         # NEW: AnthropicProvider implementation
├── config.py                # Updated: add anthropic_auth_token field
```

The provider is a single module (`anthropic.py`) that:
1. Defines `AnthropicProvider` — satisfies `LLMProvider` structurally (no inheritance)
2. Defines a factory function for registry integration
3. Is imported and registered in `providers/__init__.py`

### Data Flow

```
Caller (Agent Registry / CLI / test)
    │
    ├─ get_provider("anthropic", config)     ← registry lookup
    │       │
    │       └─ factory(config)               ← creates AnthropicProvider
    │               │
    │               ├─ resolves auth method   (api_key or auth_token)
    │               └─ creates AsyncAnthropic client
    │
    ├─ provider.validate()                   ← lightweight API call to verify credentials
    │
    ├─ provider.send_message(messages, system)
    │       │
    │       ├─ _convert_messages(messages)    ← Message models → Anthropic dict format
    │       ├─ client.messages.create(...)    ← SDK call (non-streaming)
    │       └─ return response.content[0].text
    │
    └─ provider.stream_message(messages, system)
            │
            ├─ _convert_messages(messages)
            ├─ client.messages.stream(...)    ← SDK async streaming helper
            └─ async yield text chunks
```

### Message Conversion

The `Message` model from `orchestration.core.models` must be converted to Anthropic SDK format:

```
orchestration Message           →  Anthropic message dict
─────────────────────────────      ─────────────────────────
sender="human" or "user"       →  {"role": "user", "content": "..."}
sender=<agent_name>            →  {"role": "assistant", "content": "..."}
sender="system"                →  extracted to system= parameter
message_type=system            →  extracted to system= parameter
```

Key rules:
- Messages with `sender="human"` or any non-agent sender → `role: "user"`
- Messages with `sender=<agent_name>` (the current agent) → `role: "assistant"`
- System messages are extracted and passed via the `system` parameter, not inline
- The `system` kwarg from `send_message`/`stream_message` takes precedence if provided; system messages in the list are used as fallback
- Consecutive same-role messages must be handled (Anthropic API requires alternating roles) — merge adjacent same-role messages with newline separation

## Technical Decisions

### Authentication Strategy

The Anthropic SDK supports two mutually exclusive auth mechanisms:

1. **API Key** (`X-Api-Key` header): Standard method. Passed via `api_key` parameter to `AsyncAnthropic()`. Sourced from `ProviderConfig.api_key` falling back to `Settings.anthropic_api_key`.

2. **Auth Token** (`Authorization: Bearer` header): Used for OAuth/session-based flows. Passed via `auth_token` parameter to `AsyncAnthropic()`. Sourced from `ProviderConfig.extra["auth_token"]` falling back to `Settings.anthropic_auth_token`.

**Resolution order** (fail explicitly if neither is available):
1. Check `ProviderConfig.api_key` → use API key auth
2. Check `ProviderConfig.extra["auth_token"]` → use auth token auth
3. Check `Settings.anthropic_api_key` → use API key auth
4. Check `Settings.anthropic_auth_token` → use auth token auth
5. Raise `ValueError` with clear message listing both options

**Rationale**: API key is the proven, production-ready path. Auth token infrastructure exists in the SDK today and will support future Claude Max OAuth/PKCE flows when they mature. By supporting both from day one, we avoid a breaking change later.

### Async-Only Client

Use `AsyncAnthropic` exclusively. The orchestration framework is async throughout (asyncio-based agent execution, async protocol methods). There is no need for a synchronous client.

### SDK Streaming Helper

Use the SDK's `client.messages.stream()` context manager (not raw `stream=True`) for `stream_message`. It provides:
- Typed event stream
- `.text_stream` async iterator for clean text chunk yielding
- Automatic cleanup via context manager
- Access to final message for token usage logging

### Error Mapping

Map SDK exceptions to meaningful behavior rather than leaking SDK internals:

| SDK Exception | Provider Behavior |
|---------------|-------------------|
| `AuthenticationError` (401) | `validate()` returns `False`; `send_message`/`stream_message` raise `ProviderAuthError` |
| `RateLimitError` (429) | Let SDK retry (built-in). If still failing, propagate as-is for now |
| `APIConnectionError` | `validate()` returns `False`; API calls propagate the error |
| `APITimeoutError` | Propagate as-is (SDK default timeout is 10 min, sufficient) |
| `BadRequestError` (400) | Propagate — indicates caller error (bad message format, etc.) |

Define a minimal exception hierarchy in the provider module:

```python
class ProviderError(Exception):
    """Base exception for provider errors."""

class ProviderAuthError(ProviderError):
    """Authentication failed."""

class ProviderAPIError(ProviderError):
    """API call failed after retries."""
```

### Validation Approach

`validate()` should make a real API call to confirm credentials work. Options:
- **Chosen**: Send a minimal `messages.create` with `max_tokens=1` and a trivial prompt. This exercises the full auth path and confirms the model is accessible.
- **Rejected**: Checking headers or token format only — doesn't verify the credential actually works with the API.

### No Custom Retry Logic

The Anthropic SDK has built-in retry with exponential backoff (default: 2 retries). This is sufficient. Custom retry logic would add complexity without clear benefit and could interfere with the SDK's own retry behavior.

### Default `max_tokens`

The Anthropic API requires `max_tokens` for every request. The provider uses a sensible default (`4096`) that can be overridden via `ProviderConfig.extra["max_tokens"]`. This avoids requiring callers to always specify it while allowing customization.

## Implementation Details

### AnthropicProvider Class Shape

```python
class AnthropicProvider:
    """Anthropic LLM provider using the official SDK."""

    def __init__(self, config: ProviderConfig) -> None:
        # Resolve auth, create AsyncAnthropic client, store config

    @property
    def name(self) -> str: ...       # "anthropic"

    @property
    def model(self) -> str: ...      # from config.model

    async def send_message(
        self, messages: list[Message], system: str | None = None,
    ) -> str: ...

    async def stream_message(
        self, messages: list[Message], system: str | None = None,
    ) -> AsyncIterator[str]: ...

    async def validate(self) -> bool: ...
```

Internal helpers (private):
- `_resolve_auth(config: ProviderConfig) -> dict`: Returns `{"api_key": ...}` or `{"auth_token": ...}` kwargs for client constructor
- `_convert_messages(messages: list[Message]) -> tuple[list[dict], str | None]`: Converts Message list to Anthropic format, extracting system messages. Returns `(messages_list, system_text)`.

### Settings Extension

Add one field to `Settings`:

```python
# In config.py
anthropic_auth_token: str | None = None  # ORCH_ANTHROPIC_AUTH_TOKEN
```

This parallels the existing `anthropic_api_key` field and follows the same env-var pattern.

### Provider Registration

In `providers/__init__.py`:

```python
from orchestration.providers.anthropic import AnthropicProvider
from orchestration.providers.registry import register_provider

def _anthropic_factory(config: ProviderConfig) -> AnthropicProvider:
    return AnthropicProvider(config)

register_provider("anthropic", _anthropic_factory)
```

This runs at import time, so importing `orchestration.providers` automatically registers the Anthropic provider. The registry is available immediately for `get_provider("anthropic", config)`.

### Test Strategy

All tests mock the Anthropic SDK — no real API calls.

**Unit tests** (`tests/test_anthropic_provider.py`):
- Constructor: resolves API key from config, resolves auth token from config, raises on missing credentials
- `send_message`: converts messages correctly, returns response text, handles system prompt
- `stream_message`: yields text chunks, handles system prompt
- `validate`: returns `True` on success, returns `False` on `AuthenticationError`
- Message conversion: human→user role, agent→assistant role, system message extraction, consecutive role merging
- Error mapping: auth error, rate limit passthrough, connection error

**Integration with registry** (`tests/test_providers.py` extension or new test):
- `get_provider("anthropic", config)` returns an `AnthropicProvider` instance
- Provider satisfies `isinstance(provider, LLMProvider)` check

**Mocking approach**: Use `unittest.mock.AsyncMock` to mock `AsyncAnthropic` and its `messages.create` / `messages.stream` methods. Inject the mock via constructor parameter or by patching `anthropic.AsyncAnthropic`.

## Integration Points

### Provides to Other Slices

| What | Used By | Mechanism |
|------|---------|-----------|
| Working `AnthropicProvider` | Agent Registry (102), CLI (104) | `get_provider("anthropic", config)` |
| `ProviderError` hierarchy | All consumers of provider | `from orchestration.providers.anthropic import ProviderError` |
| Registered "anthropic" factory | Any code calling `get_provider` | Auto-registered on `import orchestration.providers` |
| Auth token settings field | CLI and server startup | `Settings.anthropic_auth_token` |

### Consumes from Other Slices

| What | Source | Notes |
|------|--------|-------|
| LLMProvider Protocol | Foundation (100) | Structural contract |
| ProviderConfig, Message | Foundation (100) | Data models for config and message passing |
| Provider registry | Foundation (100) | Registration and lookup |
| Settings, get_logger | Foundation (100) | Configuration and logging |

## Success Criteria

### Functional Requirements

- `AnthropicProvider` can be instantiated with a `ProviderConfig` containing an API key
- `AnthropicProvider` can be instantiated with a `ProviderConfig` containing an auth token in `extra`
- `AnthropicProvider` raises `ValueError` when neither API key nor auth token is available
- `send_message` returns complete response text for a list of `Message` objects
- `stream_message` yields text chunks as an async iterator
- `validate` returns `True` when credentials are valid, `False` when invalid
- System messages are correctly extracted and passed to the API
- Message role conversion (human→user, agent→assistant) works correctly
- Consecutive same-role messages are merged

### Technical Requirements

- `get_provider("anthropic", config)` works after `import orchestration.providers`
- `isinstance(provider, LLMProvider)` returns `True` for `AnthropicProvider`
- All tests pass with mocked SDK (no real API calls in tests)
- `ruff check` passes with no errors
- `ruff format --check` passes
- `pyright` strict mode passes with zero errors

### Integration Requirements

- Subsequent slices (102, 104) can call `get_provider("anthropic", config)` and use the returned provider to send messages, without any additional setup beyond having credentials configured

## Risk Assessment

### Technical Risks

**Auth token / Claude Max credential flow**: The Anthropic SDK supports `auth_token` as a parameter, but the end-to-end flow for Claude Max subscribers to obtain tokens programmatically (OAuth/PKCE) is not yet production-documented. This slice builds the `auth_token` plumbing but does not implement token acquisition.

### Mitigation

- API key auth is fully functional and serves as the primary path — the framework works today with a standard API key
- Auth token support is additive and isolated — it adds a code path but doesn't complicate the API key path
- When the OAuth flow matures, a small follow-up slice can add token acquisition without changing `AnthropicProvider`

## Implementation Notes

### Development Approach

Suggested implementation order:

1. Add `anthropic_auth_token` to `Settings` — minimal change, extends config
2. Define `ProviderError` / `ProviderAuthError` exceptions — used by provider
3. Implement `_resolve_auth` helper — auth resolution logic, independently testable
4. Implement `_convert_messages` helper — message conversion, independently testable
5. Implement `AnthropicProvider.__init__` — client creation with resolved auth
6. Implement `send_message` — core message send
7. Implement `stream_message` — streaming variant
8. Implement `validate` — credential check
9. Wire registration in `providers/__init__.py`
10. Write tests for each component above

### Special Considerations

- **`max_tokens` is required**: Every Anthropic API call must include `max_tokens`. Default to `4096` via `config.extra.get("max_tokens", 4096)`.
- **Model passthrough**: The `config.model` field is passed directly to the SDK's `model` parameter. The framework does not validate model names — the API will reject invalid ones.
- **Logging**: Log at DEBUG level for API call start/completion with token usage. Log at WARNING for auth fallback paths. Log at ERROR for credential resolution failure.
