"""The per-tool-result history cap (slice 266, T20).

SC9 names the mechanism, not just the outcome: a single tool result must be truncated
*before* it enters history, so the whole-conversation ``agent.max_history_chars`` guard —
a backstop for accumulated history — is not what stops it. Asserting only that history
stayed small would pass with the cap absent, because the budget guard would have fired.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from squadron.core.models import Message
from squadron.providers.openai.agent import OpenAICompatibleAgent
from squadron.tools import limits

from .conftest import text_chunk, tool_chunk

_MODEL = "gpt-4o-mini"
_USER_MSG = Message(sender="human", recipients=["bot"], content="hello")


def _async_stream(*chunks: Any) -> AsyncMock:
    async def _gen() -> Any:
        for chunk in chunks:
            yield chunk

    mock = AsyncMock()
    mock.__aiter__ = lambda _: _gen()
    return mock


def _make_client(*streams: Any) -> Any:
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=list(streams))
    client.close = AsyncMock()
    return client


async def _run_one_tool_call(
    tmp_path: Path,
    *,
    file_bytes: int,
    max_history_chars: int,
    max_tool_result_chars: int | None = None,
) -> tuple[OpenAICompatibleAgent, list[Message]]:
    """Drive one read_file call whose result is `file_bytes` long, then a final answer."""
    (tmp_path / "big.txt").write_text("X" * file_bytes)
    read_call = tool_chunk(0, "call_1", "read_file", json.dumps({"path": "big.txt"}))
    client = _make_client(_async_stream(read_call), _async_stream(text_chunk("done")))
    agent = OpenAICompatibleAgent(
        name="bot",
        client=client,
        model=_MODEL,
        system_prompt=None,
        allowed_tools=["read_file"],
        cwd=str(tmp_path),
        max_tool_iterations=5,
        max_history_chars=max_history_chars,
        max_tool_result_chars=max_tool_result_chars,
    )
    msgs = [m async for m in agent.handle_message(_USER_MSG)]
    return agent, msgs


def _tool_entries(agent: OpenAICompatibleAgent) -> list[dict[str, Any]]:
    return [e for e in agent._history if e.get("role") == "tool"]  # pyright: ignore[reportPrivateUsage]


@pytest.mark.asyncio
async def test_oversized_result_is_truncated_before_the_append(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """SC9: the cap fires, the budget guard does not.

    ``max_history_chars`` is left generous so the budget guard cannot be what bounded the
    history — if the per-result cap were missing, the full result would sit in history and
    this test would fail.
    """
    monkeypatch.setattr(limits, "MAX_READ_BYTES", 200)
    monkeypatch.setattr(limits, "MAX_OUTPUT_BYTES", 200)
    monkeypatch.setattr(limits, "TOOL_RESULT_HEADROOM", 1.0)
    caplog.set_level(logging.WARNING)

    agent, msgs = await _run_one_tool_call(
        tmp_path, file_bytes=5_000, max_history_chars=1_000_000, max_tool_result_chars=200
    )

    assert msgs[-1].content == "done"
    entries = _tool_entries(agent)
    assert len(entries) == 1
    content = str(entries[0]["content"])
    # Truncated to the cap plus its marker — nowhere near the 5,000-character result.
    assert len(content) < 400
    assert "truncated" in content
    # read_file applies its own MAX_READ_BYTES first, so the agent sees that bounded
    # result; what matters is the agent's cap fired on top of it.
    assert "showing first 200" in content

    # The mechanism, not just the outcome: the budget guard never ran.
    assert not any("max_history_chars" in r.getMessage() for r in caplog.records)
    assert not any(
        e.get("role") == "user" and "budget" in str(e.get("content", "")).lower()
        for e in agent._history  # pyright: ignore[reportPrivateUsage]
    )


@pytest.mark.asyncio
async def test_single_result_cannot_exhaust_the_history_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The property SC9 actually asks for, stated directly."""
    monkeypatch.setattr(limits, "MAX_READ_BYTES", 100)
    monkeypatch.setattr(limits, "MAX_OUTPUT_BYTES", 100)
    monkeypatch.setattr(limits, "TOOL_RESULT_HEADROOM", 1.0)
    caplog.set_level(logging.WARNING)

    # A history budget far larger than the cap but far smaller than the raw result:
    # without the per-result cap the single result alone would blow it.
    agent, _ = await _run_one_tool_call(
        tmp_path, file_bytes=10_000, max_history_chars=2_000, max_tool_result_chars=100
    )

    assert agent._history_chars < 2_000  # pyright: ignore[reportPrivateUsage]
    assert not any("max_history_chars" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_normal_result_is_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A result under the cap passes through byte for byte."""
    monkeypatch.setattr(limits, "MAX_READ_BYTES", 10_000)
    monkeypatch.setattr(limits, "MAX_OUTPUT_BYTES", 10_000)
    monkeypatch.setattr(limits, "TOOL_RESULT_HEADROOM", 1.0)

    agent, _ = await _run_one_tool_call(
        tmp_path, file_bytes=50, max_history_chars=1_000_000, max_tool_result_chars=10_000
    )

    content = str(_tool_entries(agent)[0]["content"])
    assert content == "X" * 50
    assert "truncated" not in content


@pytest.mark.asyncio
async def test_truncation_is_observable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A silently truncated result would be a silent failure; it logs at WARNING."""
    monkeypatch.setattr(limits, "MAX_READ_BYTES", 100)
    monkeypatch.setattr(limits, "MAX_OUTPUT_BYTES", 100)
    monkeypatch.setattr(limits, "TOOL_RESULT_HEADROOM", 1.0)
    caplog.set_level(logging.WARNING)

    await _run_one_tool_call(
        tmp_path, file_bytes=5_000, max_history_chars=1_000_000, max_tool_result_chars=200
    )

    assert any("truncating" in r.getMessage().lower() for r in caplog.records)


@pytest.mark.asyncio
async def test_cap_scales_with_the_history_budget() -> None:
    """Issue #80: the two limits must not drift apart.

    A fixed per-result cap let one result take a quarter of the default budget, so four
    full-size results exhausted it. Deriving the cap keeps a plausible number of tool calls
    inside the budget at any configured size.
    """
    # An operator-configured value above the floor is honored as given.
    assert limits.resolve_tool_result_cap(500_000) == 500_000
    # One below it is raised, not honored — it would mangle correct results.
    assert limits.resolve_tool_result_cap(1_000) == limits.min_tool_result_chars()


def test_cap_never_cuts_below_a_tools_own_output_bound() -> None:
    """Regression: the cap is a backstop, not a second truncation of ordinary results.

    Every built-in tool already bounds its output at MAX_OUTPUT_BYTES and appends its own
    "showing first N" marker. A cap below that re-truncates a correctly-truncated result,
    replacing that marker with a cut mid-line. Observed live: a review that had been making
    45 tool calls made 1, and returned UNKNOWN with no findings.
    """
    for configured in (1_000, 100_000, 400_000, 1_000_000):
        resolved = limits.resolve_tool_result_cap(configured)
        assert resolved > limits.MAX_OUTPUT_BYTES
        # read_file returns up to MAX_READ_BYTES, which the first fix overlooked: a
        # 167,573-character read was re-truncated at 96,000 in a live run.
        assert resolved > limits.MAX_READ_BYTES


def test_default_budget_admits_a_realistic_number_of_tool_calls() -> None:
    """The budget, not the cap, is what bounds a tool-using run in practice."""
    from squadron.config.keys import CONFIG_KEYS

    budget = CONFIG_KEYS["agent.max_history_chars"].default
    cap = CONFIG_KEYS["agent.max_tool_result_chars"].default
    assert isinstance(budget, int) and isinstance(cap, int)
    # The shipped default must already satisfy the floor — no clamp warning on a fresh
    # install — and leave room for several full-size results.
    assert cap == limits.resolve_tool_result_cap(cap)
    assert budget // limits.MAX_OUTPUT_BYTES >= 15


# ---------------------------------------------------------------------------
# The iteration budget reserves a finalize turn
#
# Observed live: raising agent.max_history_chars to 1M removed the only thing that
# had been stopping this model. The history-budget guard doubled as an accidental
# completion trigger — once it no longer fired, the loop ran to
# max_tool_iterations and raised, discarding every tool result it had gathered.
# ---------------------------------------------------------------------------


async def _run_until(
    tmp_path: Path, *, max_tool_iterations: int, stops_after: int | None
) -> tuple[OpenAICompatibleAgent, list[Message], object]:
    """Drive a model that keeps calling tools, optionally answering after N turns."""
    (tmp_path / "a.txt").write_text("content\n")
    read_call = tool_chunk(0, "call_1", "read_file", json.dumps({"path": "a.txt"}))

    turns = 0

    def _next_stream(*_args: object, **kwargs: object) -> AsyncMock:
        nonlocal turns
        turns += 1
        # A model that finalizes only when tools are withdrawn.
        withdrawn = not kwargs.get("tools") or kwargs.get("tools") is None
        if stops_after is not None and turns > stops_after:
            return _async_stream(text_chunk("final answer"))
        if withdrawn:
            return _async_stream(text_chunk("final answer"))
        return _async_stream(read_call)

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=_next_stream)
    client.close = AsyncMock()

    agent = OpenAICompatibleAgent(
        name="bot",
        client=client,
        model=_MODEL,
        system_prompt=None,
        allowed_tools=["read_file"],
        cwd=str(tmp_path),
        max_tool_iterations=max_tool_iterations,
        max_history_chars=10_000_000,
    )
    msgs = [m async for m in agent.handle_message(_USER_MSG)]
    return agent, msgs, client


@pytest.mark.asyncio
async def test_last_iteration_withdraws_tools_and_gets_an_answer(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A model that would otherwise loop forever still produces a usable response."""
    caplog.set_level(logging.WARNING)

    _, msgs, client = await _run_until(tmp_path, max_tool_iterations=4, stops_after=None)

    assert msgs[-1].content == "final answer"
    # The last call offered no tools.
    assert not client.chat.completions.create.call_args_list[-1].kwargs.get("tools")
    assert any("withdrawing tools" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_finalize_notice_precedes_the_turn_it_explains(tmp_path: Path) -> None:
    """The model must see why its tools vanished, not be told afterwards."""
    agent, _, _ = await _run_until(tmp_path, max_tool_iterations=3, stops_after=None)

    history = agent._history  # pyright: ignore[reportPrivateUsage]
    notice_index = next(
        i
        for i, e in enumerate(history)
        if e.get("role") == "user" and "tool-iteration budget" in str(e.get("content", ""))
    )
    # The assistant's final answer comes after the notice, not before it.
    assert any(
        e.get("role") == "assistant" and "final answer" in str(e.get("content", ""))
        for e in history[notice_index:]
    )


@pytest.mark.asyncio
async def test_a_model_that_finishes_early_is_unaffected(tmp_path: Path) -> None:
    """The reserved turn costs nothing when the model stops on its own."""
    _, msgs, client = await _run_until(tmp_path, max_tool_iterations=20, stops_after=2)

    assert msgs[-1].content == "final answer"
    # Nowhere near the cap, so tools were still on offer throughout.
    assert client.chat.completions.create.call_count <= 4
