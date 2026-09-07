"""Grep input bounds: the pattern cap and the read-truncation marker (slice 266, T18).

Both limits are monkeypatched to small values rather than building megabyte fixtures —
``limits`` constants are read as module attributes at call time precisely so this works.
"""

from __future__ import annotations

import logging
import time
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


# ---------------------------------------------------------------------------
# Issue #79 — the walk skips dependency trees, and reports the right cause
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dependency_directories_are_not_searched(tmp_path: Path) -> None:
    """`.venv` and friends are the bulk of a real tree and never the code under review."""
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "dep.py").write_text("NEEDLE from a dependency\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "pkg.js").write_text("NEEDLE from node_modules\n")
    (tmp_path / "src.py").write_text("NEEDLE in project code\n")

    content, is_error = await _grep(tmp_path, {"pattern": "NEEDLE"})

    assert not is_error
    assert "src.py" in content
    assert ".venv" not in content
    assert "node_modules" not in content


@pytest.mark.asyncio
async def test_an_explicitly_named_skip_directory_is_still_searched(tmp_path: Path) -> None:
    """Pruning applies to descent, not to a root the caller asked for by name."""
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "dep.py").write_text("NEEDLE inside the venv\n")

    content, is_error = await _grep(tmp_path, {"pattern": "NEEDLE", "path": ".venv"})

    assert not is_error
    assert "dep.py" in content


@pytest.mark.asyncio
async def test_walk_timeout_blames_the_tree_not_the_pattern(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Issue #79: telling a model to simplify an already-trivial pattern is unfollowable."""
    for index in range(40):
        (tmp_path / f"f{index}.txt").write_text("some content\n")
    # A budget already spent: the walk check trips on the first candidate.
    monkeypatch.setattr(limits, "GREP_TIMEOUT_S", -1.0)

    content, is_error = await _grep(tmp_path, {"pattern": "literal"})

    assert is_error
    assert "too large" in content
    assert "narrow it" in content
    # The advice that was wrong for a walk timeout must not appear.
    assert "simpler or more anchored pattern" not in content


@pytest.mark.asyncio
async def test_pattern_timeout_still_blames_the_pattern(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The engine-level timeout is the one case where simplifying the pattern is the fix."""
    # Genuine catastrophic backtracking. Note the `regex` module optimizes away the
    # textbook `(a+)+$` form, so the alternation variant is used — verified to time out.
    (tmp_path / "a.txt").write_text("a" * 30 + "!\n")
    monkeypatch.setattr(limits, "GREP_TIMEOUT_S", 0.2)

    content, is_error = await _grep(tmp_path, {"pattern": r"(a|a)*$"})

    assert is_error
    assert "simpler or more anchored pattern" in content


@pytest.mark.asyncio
async def test_partial_matches_survive_a_walk_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial answer beats none, so long as it says it is partial.

    The clock is pinned to a concrete event — the read of the decoy file — rather than to a
    count of monotonic() calls, which would couple the test to the loop's internals and
    could start passing vacuously if that structure changed.
    """
    (tmp_path / "a_hit.txt").write_text("NEEDLE\n")
    (tmp_path / "z_decoy.txt").write_text("NEEDLE\n")

    real_monotonic = time.monotonic
    start = real_monotonic()
    expired = False

    def _fake_monotonic() -> float:
        # Time stands still until the decoy is opened, then jumps past any deadline.
        return start + (999.0 if expired else 0.0)

    real_open = Path.open

    def _open_spy(self: Path, *args: object, **kwargs: object) -> object:
        nonlocal expired
        if self.name == "z_decoy.txt":
            expired = True
        return real_open(self, *args, **kwargs)  # pyright: ignore[reportCallIssue,reportArgumentType]

    monkeypatch.setattr(time, "monotonic", _fake_monotonic)
    monkeypatch.setattr(Path, "open", _open_spy)

    content, is_error = await _grep(tmp_path, {"pattern": "NEEDLE"})

    # The first file matched before the clock jumped; that match must survive.
    assert "a_hit.txt" in content, "the match found before the cutoff was discarded"
    assert not is_error, "a partial result is an incomplete answer, not an error"
    assert "search abandoned" in content
    assert "too large" in content


@pytest.mark.asyncio
async def test_runaway_argument_is_not_reported_as_a_long_pattern(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A half-megabyte 'pattern' is a malfunction, not a pattern the model can shorten.

    Observed live: kimi27 emitted a 531,571-character pattern argument. The agentic loop
    has seen the same runaway produce a ~400KB argument that failed JSON parsing; this one
    parsed cleanly and reached the tool. Telling that model to "shorten it" invites a retry
    of the same broken output.
    """
    (tmp_path / "a.txt").write_text("hello\n")

    with caplog.at_level(logging.WARNING, logger="squadron.tools.builtin.search_tools"):
        content, is_error = await _grep(tmp_path, {"pattern": "x" * 531_571})

    assert is_error
    assert "not a search pattern" in content
    assert "Re-issue the call" in content
    assert "shorten it" not in content
    # A runaway is an operator-visible event, unlike a routine over-long pattern.
    assert any("runaway tool argument" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_merely_long_pattern_still_says_shorten_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ordinary over-cap case keeps the advice the model can actually act on."""
    monkeypatch.setattr(limits, "MAX_PATTERN_CHARS", 10)
    (tmp_path / "a.txt").write_text("hello\n")

    content, is_error = await _grep(tmp_path, {"pattern": "y" * 50})

    assert is_error
    assert "shorten it" in content
    assert "not a search pattern" not in content
