---
slice: openai-provider-core
project: orchestration
lld: project-documents/user/slices/111-slice.openai-provider-core.md
dependencies: [foundation]
projectState: M1 complete and published. Review workflows and M1 polish done. SDK provider, agent registry, and CLI all operational. Expanding to multi-provider support.
status: not started
dateCreated: 20260226
dateUpdated: 20260226
---

## Context Summary

- Working on **openai-provider-core** (slice 111)
- Implements `OpenAICompatibleProvider` and `OpenAICompatibleAgent` against the OpenAI Chat Completions API
- Single implementation covers OpenAI, OpenRouter, Ollama/vLLM, and Gemini-compatible endpoints via `base_url`
- Validates that `AgentProvider` Protocol generalizes beyond Anthropic — no core engine changes required
- Also fixes a provider auto-loader gap in `spawn.py` and adds `--base-url` CLI flag
- Depends on Foundation slice only
- Next slice: 112 (Provider Variants & Registry — OpenRouter, local, Gemini configs + model alias profiles)
- Full design: `project-documents/user/slices/111-slice.openai-provider-core.md`

---

## Tasks

- [ ] **T1: Add openai dependency**
  - [ ] Add `openai>=1.0.0` to `pyproject.toml` `[project.dependencies]` list
  - [ ] Run `uv sync` to install; resolve any conflicts
  - [ ] Success: `python -c "import openai; print(openai.__version__)"` prints a version ≥ 1.0.0

- [ ] **T2: Create test infrastructure for providers/openai**
  - [ ] Create `tests/providers/openai/__init__.py` (empty)
  - [ ] Create `tests/providers/openai/conftest.py` with:
    - `mock_async_openai` fixture — `MagicMock` of `AsyncOpenAI` with `chat.completions.create` set to `AsyncMock`; `close` set to `AsyncMock`
    - `text_chunk(content)` factory — returns a minimal `ChatCompletionChunk` with `delta.content` set and `delta.tool_calls` as `None`
    - `tool_chunk(index, id, name, args_fragment)` factory — returns a `ChatCompletionChunk` with `delta.tool_calls` populated
  - [ ] Success: `pytest tests/providers/openai/` runs (0 tests, 0 errors)

- [ ] **T3: Implement translation.py**
  - [ ] Create `src/orchestration/providers/openai/translation.py`
  - [ ] `build_text_message(text, agent_name, model) -> Message | None` — returns a `chat` Message; returns `None` if text is empty/whitespace
  - [ ] `build_tool_call_message(tool_call: dict, agent_name) -> Message` — returns a `system` Message; metadata: `{"provider": "openai", "type": "tool_call", "tool_call_id": ..., "tool_name": ..., "tool_arguments": ...}`
  - [ ] `build_messages(text_buffer, tool_calls_list, agent_name, model) -> list[Message]` — calls both builders; text message first (if non-empty), then tool call messages
  - [ ] Success: module importable; all three functions present with correct signatures

- [ ] **T4: Test translation.py**
  - [ ] `test_build_text_message_non_empty` — returns chat Message with correct content, sender=agent_name, recipients=["all"], metadata has provider and model
  - [ ] `test_build_text_message_empty_returns_none` — empty string → `None`
  - [ ] `test_build_tool_call_message_metadata` — all four metadata keys present with correct values
  - [ ] `test_build_messages_text_only` — text set, no tool calls → one chat Message
  - [ ] `test_build_messages_tool_calls_only` — two tool calls, no text → two system Messages, no chat Message
  - [ ] `test_build_messages_mixed` — text + one tool call → chat Message first, system Message second
  - [ ] `test_build_messages_empty` — empty text, no tool calls → empty list
  - [ ] Success: all tests pass; `ruff check src/orchestration/providers/openai/translation.py` clean

- [ ] **T5: Implement provider.py**
  - [ ] Create `src/orchestration/providers/openai/provider.py`
  - [ ] `OpenAICompatibleProvider` class:
    - `provider_type` property → `"openai"`
    - `create_agent(config)` — resolve API key: `config.api_key` → `os.environ.get("OPENAI_API_KEY")` → raise `ProviderAuthError`; raise `ProviderError` if `config.model is None`; construct `AsyncOpenAI(api_key=..., base_url=config.base_url)`; return `OpenAICompatibleAgent`
    - `validate_credentials()` — check `openai` importable AND `OPENAI_API_KEY` env var is set; return bool, never raise
  - [ ] Success: class satisfies `AgentProvider` Protocol; pyright reports no errors on this module

- [ ] **T6: Test provider.py**
  - [ ] `test_provider_type` — `provider_type == "openai"`
  - [ ] `test_create_agent_uses_config_api_key` — `config.api_key` set → passed to `AsyncOpenAI` constructor
  - [ ] `test_create_agent_falls_back_to_env_var` — `config.api_key` None, env var set → uses env var
  - [ ] `test_create_agent_raises_auth_error_no_key` — neither source has a key → `ProviderAuthError`
  - [ ] `test_create_agent_raises_error_model_none` — `config.model` is None → `ProviderError`
  - [ ] `test_create_agent_passes_base_url` — `config.base_url` set → `AsyncOpenAI` constructed with it
  - [ ] `test_validate_credentials_true` — package importable, env var set → True
  - [ ] `test_validate_credentials_false_no_env` — env var absent → False; no exception raised
  - [ ] Success: all tests pass; ruff clean

- [ ] **T7: Implement agent.py**
  - [ ] Create `src/orchestration/providers/openai/agent.py`
  - [ ] `OpenAICompatibleAgent.__init__(name, client, model, system_prompt)`:
    - `_history: list[dict[str, Any]] = []`; append system entry if `system_prompt` is not None
    - `_state = AgentState.idle`
  - [ ] Properties: `name`, `agent_type` → `"api"`, `state`
  - [ ] `handle_message(message)` as async generator:
    1. State → `processing`; append user entry to `_history`
    2. Call `client.chat.completions.create(model=..., messages=_history, stream=True)`
    3. Iterate stream: accumulate `delta.content` into text buffer; accumulate `delta.tool_calls` fragments by `index` into a dict
    4. After stream ends, flatten accumulated tool_calls dict into ordered list
    5. Call `translation.build_messages(text, tool_calls, name, model)` and yield each Message
    6. Append assistant turn to `_history` (text content and/or tool_calls in OpenAI assistant format)
    7. In `finally`: state → `idle`
    8. Map openai exceptions → ProviderError hierarchy (see slice design §Error Mapping table)
  - [ ] `shutdown()` — `await self._client.close()`; state → `terminated`
  - [ ] Success: class satisfies `Agent` Protocol; pyright reports no errors on this module

- [ ] **T8: Test agent.py**
  - [ ] `test_initial_state_is_idle`
  - [ ] `test_system_prompt_prepended_to_history` — system_prompt set → `_history[0]["role"] == "system"`
  - [ ] `test_no_system_prompt_history_empty` — no system_prompt → history empty before first message
  - [ ] `test_handle_message_appends_user_entry` — after call, history contains user entry
  - [ ] `test_handle_message_appends_assistant_entry` — after call, history contains assistant entry
  - [ ] `test_handle_message_yields_chat_message` — text stream → one chat Message yielded
  - [ ] `test_handle_message_multi_turn_history_grows` — two sequential calls → history has user, assistant, user, assistant entries
  - [ ] `test_handle_message_yields_system_for_tool_call` — tool_call stream → one system Message yielded
  - [ ] `test_state_is_idle_after_success` — state returns to idle after handle_message completes
  - [ ] `test_error_auth` — `openai.AuthenticationError` raised → `ProviderAuthError`; state returns to idle
  - [ ] `test_error_rate_limit` — `openai.RateLimitError` → `ProviderAPIError` with `status_code=429`
  - [ ] `test_error_api_status` — `openai.APIStatusError(status_code=503)` → `ProviderAPIError(status_code=503)`
  - [ ] `test_error_connection` — `openai.APIConnectionError` → `ProviderError`
  - [ ] `test_error_timeout` — `openai.APITimeoutError` → `ProviderTimeoutError`
  - [ ] `test_shutdown_closes_client_and_sets_terminated` — `shutdown()` calls `client.close()`; state → terminated
  - [ ] Success: all tests pass; ruff clean

- [ ] **T9: Implement __init__.py (auto-registration)**
  - [ ] Create `src/orchestration/providers/openai/__init__.py`
  - [ ] Instantiate `_provider = OpenAICompatibleProvider()`; call `register_provider("openai", _provider)`
  - [ ] Set `__all__ = ["OpenAICompatibleProvider", "OpenAICompatibleAgent"]`
  - [ ] Success: importing `orchestration.providers.openai` succeeds; `get_provider("openai")` returns the instance

- [ ] **T10: Test registration**
  - [ ] Follow pattern from `tests/providers/sdk/test_registration.py` (clean-registry fixture)
  - [ ] `test_openai_in_list_after_import` — import module → "openai" in `list_providers()`
  - [ ] `test_get_provider_returns_openai_provider` — `isinstance(get_provider("openai"), OpenAICompatibleProvider)`
  - [ ] `test_provider_type_is_openai`
  - [ ] Success: all tests pass; `pytest tests/providers/openai/` fully green

- [ ] **T11: Commit providers/openai**
  - [ ] `pytest tests/providers/openai/` — all green
  - [ ] `ruff check src/orchestration/providers/openai/` — clean
  - [ ] `pyright src/orchestration/providers/openai/` — zero errors
  - [ ] `git add` new provider files and test files; commit: `feat: add OpenAI-compatible provider`

- [ ] **T12: Add provider auto-loader to spawn.py**
  - [ ] Add `_load_provider(name: str) -> None` to `src/orchestration/cli/commands/spawn.py`; uses `importlib.import_module(f"orchestration.providers.{name}")` in try/except ImportError (silent)
  - [ ] Call `_load_provider(config.provider)` in `_spawn()` before `registry.spawn(config)`
  - [ ] Success: existing `pytest tests/cli/test_spawn.py` still passes unchanged

- [ ] **T13: Test provider auto-loader**
  - [ ] `test_load_provider_calls_import_module` — patch `importlib.import_module`; call `_load_provider("openai")`; verify called with `"orchestration.providers.openai"`
  - [ ] `test_load_provider_silences_import_error` — patch import_module to raise ImportError; call `_load_provider`; no exception propagates
  - [ ] `test_spawn_triggers_load_provider` — patch `_load_provider` and `get_registry`; invoke spawn; verify `_load_provider` called with the provider name
  - [ ] Success: all tests pass; ruff clean

- [ ] **T14: Add --base-url flag to spawn.py**
  - [ ] Add `base_url: str | None = typer.Option(None, "--base-url", help="Base URL for OpenAI-compatible endpoints (e.g. http://localhost:11434/v1)")` to `spawn()` signature
  - [ ] Pass `base_url=base_url` to `AgentConfig(...)` constructor
  - [ ] Success: `orchestration spawn --help` shows `--base-url` option; existing spawn tests pass

- [ ] **T15: Test --base-url flag**
  - [ ] `test_base_url_passed_to_agent_config` — invoke spawn with `--base-url http://localhost:11434/v1`; verify `AgentConfig.base_url` matches in the `registry.spawn` call
  - [ ] `test_base_url_defaults_to_none` — spawn without `--base-url`; `AgentConfig.base_url` is None
  - [ ] Success: both tests pass; ruff clean on spawn.py

- [ ] **T16: Full validation pass**
  - [ ] `pytest` (full suite) — all green, no errors
  - [ ] `ruff check src/` — clean
  - [ ] `pyright src/` — zero errors
  - [ ] Success: all three checks pass

- [ ] **T17: Commit CLI changes**
  - [ ] `git add` spawn.py and T12-T15 test files
  - [ ] Commit: `feat: add provider auto-loader and --base-url to spawn command`
  - [ ] Success: `git status` clean; `orchestration spawn --help` shows `--base-url`

---

## Implementation Notes

- **AsyncOpenAI mock**: `client.chat.completions.create` is called with `stream=True`. The return value must be async-iterable (implement `__aiter__`). Use `AsyncMock` with `__aiter__` returning an async iterator over synthetic chunks.
- **Tool call accumulation**: OpenAI streams tool calls as chunks with an `index` field. Each chunk adds content to the call at that index. Accumulate into `dict[int, dict]`, then flatten to list after stream ends. Prefer the SDK's `stream.get_final_message()` helper if it simplifies the implementation — see openai SDK docs.
- **History type**: Use `list[dict[str, Any]]` (not `list[dict[str, str]]`) because tool call entries include nested structures.
- **Auto-loader retroactive benefit**: After T12, `orchestration spawn --type sdk` also benefits — the SDK provider module is imported on demand rather than requiring a pre-existing import chain.
