"""Grep input bounds: the pattern cap and the read-truncation marker (slice 266, T18).

Both limits are monkeypatched to small values rather than building megabyte fixtures —
``limits`` constants are read as module attributes at call time precisely so this works.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from squadron.tools import limits, materialize
from squadron.tools.builtin import GREP_NAME


async def _grep(jail: Path, args: dict[str, object]) -> tuple[str, bool]:
    executor = materialize([GREP_NAME], str(jail))[GREP_NAME]
    result = await executor(args)
    return result.content, result.is_error


# ---------------------------------------------------------------------------
# T16 — the pattern cap (SC7)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_over_long_pattern_is_returned_as_an_error_not_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC7: the model supplied the pattern, so it gets a result it can act on."""
    monkeypatch.setattr(limits, "MAX_PATTERN_CHARS", 10)
    (tmp_path / "a.txt").write_text("hello\n")

    content, is_error = await _grep(tmp_path, {"pattern": "x" * 50})

    assert is_error
    assert "50 characters" in content
    assert "10-character limit" in content


@pytest.mark.asyncio
async def test_pattern_at_the_cap_is_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The bound is inclusive: a pattern exactly at the limit still runs."""
    monkeypatch.setattr(limits, "MAX_PATTERN_CHARS", 5)
    (tmp_path / "a.txt").write_text("hello\n")

    content, is_error = await _grep(tmp_path, {"pattern": "hello"})

    assert not is_error
    assert "a.txt:1:hello" in content


@pytest.mark.asyncio
async def test_normal_pattern_is_unaffected(tmp_path: Path) -> None:
    """The default cap does not interfere with ordinary use."""
    (tmp_path / "a.txt").write_text("findme\n")

    content, is_error = await _grep(tmp_path, {"pattern": "findme"})

    assert not is_error
    assert "a.txt:1:findme" in content


@pytest.mark.asyncio
async def test_over_long_pattern_never_reaches_the_regex_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The point of the cap: compilation is where a pathological pattern does its damage.

    Asserting only on the returned message would still pass if the check ran *after*
    ``regex.compile``, which is the bug this bound exists to prevent.
    """
    monkeypatch.setattr(limits, "MAX_PATTERN_CHARS", 10)
    (tmp_path / "a.txt").write_text("hello\n")

    compiled: list[str] = []
    import regex

    real_compile = regex.compile

    def _spy(pattern: str, *args: object, **kwargs: object) -> object:
        compiled.append(pattern)
        return real_compile(pattern, *args, **kwargs)  # pyright: ignore[reportCallIssue]

    monkeypatch.setattr(regex, "compile", _spy)

    _, is_error = await _grep(tmp_path, {"pattern": "y" * 50})

    assert is_error
    assert compiled == [], "the over-long pattern was compiled despite the cap"


# ---------------------------------------------------------------------------
# T17 — the read-truncation marker (SC8)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_beyond_the_read_cap_produces_a_marker_naming_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC8: no match is dropped without saying so.

    Without the marker this file reports as a clean "no match" — the silent failure the
    project's no-fallback rule forbids.
    """
    monkeypatch.setattr(limits, "MAX_READ_BYTES", 32)
    big = tmp_path / "big.txt"
    big.write_text("A" * 100 + "\nNEEDLE\n")

    content, is_error = await _grep(tmp_path, {"pattern": "NEEDLE"})

    assert not is_error
    assert "big.txt" in content
    assert "first 32 bytes" in content
    assert "not seen" in content


@pytest.mark.asyncio
async def test_untruncated_file_gets_no_marker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A file read in full must not be labelled as partially searched."""
    monkeypatch.setattr(limits, "MAX_READ_BYTES", 1_000)
    (tmp_path / "small.txt").write_text("NEEDLE\n")

    content, _ = await _grep(tmp_path, {"pattern": "NEEDLE"})

    assert "small.txt:1:NEEDLE" in content
    assert "not seen" not in content


@pytest.mark.asyncio
async def test_marker_accompanies_matches_found_before_the_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial search that did match still says it was partial."""
    monkeypatch.setattr(limits, "MAX_READ_BYTES", 32)
    (tmp_path / "big.txt").write_text("NEEDLE\n" + "B" * 200 + "\nNEEDLE\n")

    content, _ = await _grep(tmp_path, {"pattern": "NEEDLE"})

    assert "big.txt:1:NEEDLE" in content
    assert "not seen" in content


# ---------------------------------------------------------------------------
# Both bounds trip the baseline DEBUG tool logging (T18)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pattern_cap_is_observable_in_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """An operator on -vv must be able to tell repeated cap hits from routine tool use."""
    monkeypatch.setattr(limits, "MAX_PATTERN_CHARS", 10)
    (tmp_path / "a.txt").write_text("hello\n")

    # The tool logger's own level, not just the handler's: a prior CLI invocation in the
    # same process can leave it pinned above DEBUG (issue #78).
    logging.getLogger("squadron.tools.builtin").setLevel(logging.DEBUG)
    with caplog.at_level(logging.DEBUG, logger="squadron.tools.builtin"):
        await _grep(tmp_path, {"pattern": "z" * 50})

    assert any("limit" in r.message for r in caplog.records)
