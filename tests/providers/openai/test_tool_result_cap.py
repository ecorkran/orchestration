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
    tmp_path: Path, *, file_bytes: int, max_history_chars: int
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
    monkeypatch.setattr(limits, "MIN_TOOL_RESULT_CHARS", 200)
    monkeypatch.setattr(limits, "TOOL_RESULT_HISTORY_FRACTION", 0.0)
    caplog.set_level(logging.WARNING)

    agent, msgs = await _run_one_tool_call(tmp_path, file_bytes=5_000, max_history_chars=1_000_000)

    assert msgs[-1].content == "done"
    entries = _tool_entries(agent)
    assert len(entries) == 1
    content = str(entries[0]["content"])
    # Truncated to the cap plus its marker — nowhere near the 5,000-character result.
    assert len(content) < 400
    assert "truncated" in content
    assert "5000 characters" in content

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
    monkeypatch.setattr(limits, "MIN_TOOL_RESULT_CHARS", 100)
    monkeypatch.setattr(limits, "TOOL_RESULT_HISTORY_FRACTION", 0.0)
    caplog.set_level(logging.WARNING)

    # A history budget far larger than the cap but far smaller than the raw result:
    # without the per-result cap the single result alone would blow it.
    agent, _ = await _run_one_tool_call(tmp_path, file_bytes=10_000, max_history_chars=2_000)

    assert agent._history_chars < 2_000  # pyright: ignore[reportPrivateUsage]
    assert not any("max_history_chars" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_normal_result_is_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A result under the cap passes through byte for byte."""
    monkeypatch.setattr(limits, "MIN_TOOL_RESULT_CHARS", 10_000)
    monkeypatch.setattr(limits, "TOOL_RESULT_HISTORY_FRACTION", 0.0)

    agent, _ = await _run_one_tool_call(tmp_path, file_bytes=50, max_history_chars=1_000_000)

    content = str(_tool_entries(agent)[0]["content"])
    assert content == "X" * 50
    assert "truncated" not in content


@pytest.mark.asyncio
async def test_truncation_is_observable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A silently truncated result would be a silent failure; it logs at WARNING."""
    monkeypatch.setattr(limits, "MIN_TOOL_RESULT_CHARS", 100)
    monkeypatch.setattr(limits, "TOOL_RESULT_HISTORY_FRACTION", 0.0)
    caplog.set_level(logging.WARNING)

    await _run_one_tool_call(tmp_path, file_bytes=5_000, max_history_chars=1_000_000)

    assert any("truncating" in r.getMessage().lower() for r in caplog.records)


@pytest.mark.asyncio
async def test_cap_scales_with_the_history_budget() -> None:
    """Issue #80: the two limits must not drift apart.

    A fixed per-result cap let one result take a quarter of the default budget, so four
    full-size results exhausted it. Deriving the cap keeps a plausible number of tool calls
    inside the budget at any configured size.
    """
    assert limits.max_tool_result_chars(400_000) == 20_000
    assert limits.max_tool_result_chars(1_000_000) == 50_000
    # Room for at least 15 maximum-size results at any realistic budget — the observed
    # failure was a 45-call review forced to finalize.
    for budget in (200_000, 400_000, 1_000_000):
        assert budget // limits.max_tool_result_chars(budget) >= 15


def test_cap_never_shrinks_below_a_usable_floor() -> None:
    """A small configured budget must not make tool results useless."""
    assert limits.max_tool_result_chars(1_000) == limits.MIN_TOOL_RESULT_CHARS
