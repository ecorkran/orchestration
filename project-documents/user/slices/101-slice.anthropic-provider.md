---
docType: slice-design
slice: anthropic-provider
project: orchestration
parent: user/architecture/100-slices.orchestration-v2.md
dependencies: [foundation]
interfaces: [agent-registry, cli-foundation, additional-llm-providers]
status: not started
dateCreated: 20260218
dateUpdated: 20260219
---

# Slice Design: Anthropic Provider

## Overview

Implement a concrete `AnthropicProvider` class that satisfies the `LLMProvider` Protocol established in the foundation slice. This is the first real provider — it connects the orchestration framework to the Anthropic Messages API, enabling agents to send and receive LLM completions. Authentication uses API keys (`ANTHROPIC_API_KEY`), the only method directly supported by the official Anthropic Python SDK.

## Value

Architectural enablement and direct M1 milestone dependency. Without a working LLM provider, no agent can generate responses — the Agent Registry (slice 102), CLI (slice 104), and every downstream slice that touches LLM output are blocked. This slice transforms the orchestration skeleton into a system that can actually call Claude.

## Technical Scope

### Included

- `AnthropicProvider` class implementing the full `LLMProvider` Protocol
- API key authentication via `ProviderConfig.api_key` or `ORCH_ANTHROPIC_API_KEY` (Settings)
- Non-streaming message send (`send_message`)
- Streaming message send (`stream_message`) using the SDK's async streaming helper
- Credential validation (`validate`) that makes a lightweight API call
- Message format conversion: `orchestration.core.models.Message` to/from Anthropic SDK message dicts
- Provider self-registration with the provider registry
- Structured logging for API calls, auth events, and errors
- Comprehensive test suite using mocked SDK calls

### Excluded

- Claude Max / OAuth bearer token flows (the official Python SDK does not support `auth_token`; Max subscription token usage requires an external gateway/proxy layer such as LiteLLM, which is outside this slice's scope)
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
├── config.py                # Unchanged (already has anthropic_api_key)
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
    │               ├─ resolves api_key       (config → Settings → error)
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

The official Anthropic Python SDK supports one authentication method:

**API Key** (`X-Api-Key` header): Passed via `api_key` parameter to `AsyncAnthropic()`, or auto-loaded from the `ANTHROPIC_API_KEY` environment variable.

**Resolution order** (fail explicitly if not available):
1. Check `ProviderConfig.api_key` → use directly
2. Check `Settings.anthropic_api_key` → use as fallback
3. Raise `ValueError` with clear error message

The SDK does not have a native `auth_token` parameter. Claude Max / OAuth bearer token usage requires an external gateway layer (e.g., LiteLLM) that forwards `Authorization: Bearer` headers on the caller's behalf — the SDK itself only speaks API keys. If gateway-based auth becomes relevant, it can be supported in a future slice by allowing a custom `base_url` in `ProviderConfig.extra` to point at the gateway, while still using `api_key` for the gateway's own auth.

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
        # Resolve API key, create AsyncAnthropic client, store config

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
- `_resolve_api_key(config: ProviderConfig) -> str`: Checks config then Settings, raises `ValueError` if not found.
- `_convert_messages(messages: list[Message]) -> tuple[list[dict], str | None]`: Converts Message list to Anthropic format, extracting system messages. Returns `(messages_list, system_text)`.

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
- Constructor: resolves API key from config, resolves API key from Settings fallback, raises on missing credentials
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
- `AnthropicProvider` falls back to `Settings.anthropic_api_key` when `ProviderConfig.api_key` is `None`
- `AnthropicProvider` raises `ValueError` when no API key is available from either source
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

**Claude Max / OAuth gateway integration**: The official SDK only supports API key auth directly. Claude Max subscribers who want to use their subscription programmatically need an external gateway (e.g., LiteLLM) that handles OAuth token acquisition and forwards bearer tokens. This is outside the SDK's scope and outside this slice's scope.

### Mitigation

- API key auth covers all standard use cases — the framework works today with a Console API key
- The `ProviderConfig.extra` dict and `base_url` override provide extension points for future gateway integration without changing the provider class itself
- A future slice can add gateway support (custom `base_url` + gateway auth) if Max subscription usage becomes a priority

## Implementation Notes

### Development Approach

Suggested implementation order:

1. Define `ProviderError` / `ProviderAuthError` exceptions — used by provider
2. Implement `_resolve_api_key` helper — API key resolution logic, independently testable
3. Implement `_convert_messages` helper — message conversion, independently testable
4. Implement `AnthropicProvider.__init__` — client creation with resolved API key
5. Implement `send_message` — core message send
6. Implement `stream_message` — streaming variant
7. Implement `validate` — credential check
8. Wire registration in `providers/__init__.py`
9. Write tests for each component above

### Special Considerations

- **`max_tokens` is required**: Every Anthropic API call must include `max_tokens`. Default to `4096` via `config.extra.get("max_tokens", 4096)`.
- **Model passthrough**: The `config.model` field is passed directly to the SDK's `model` parameter. The framework does not validate model names — the API will reject invalid ones.
- **Logging**: Log at DEBUG level for API call start/completion with token usage. Log at WARNING for Settings fallback (no API key in config). Log at ERROR for credential resolution failure.
