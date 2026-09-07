"""Symlink escapes from the tool jail (slice 266, T15).

``_resolve_in_jail`` vets the *entry* path a model supplies. It cannot vet the entries a
walk discovers, and both ``grep`` and ``list_files`` walk: ``Path.is_file()`` follows
symlinks, so a link inside the jail pointing outside it looks like an ordinary file.

Two routes are covered, each for both tools:

* a symlinked **file** whose target is outside the jail;
* a symlinked **directory** whose target is outside the jail.

The directory case is version-dependent. On Python <= 3.12 ``rglob`` recurses *into*
symlinked directories; on 3.13+ it yields the link itself but does not descend. On 3.13+ a
test that asserted only "the outside content did not appear" would therefore pass whether or
not the guard exists. Every case here asserts the guard was actually **reached** — via its
WARNING — so none of them can pass vacuously.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from squadron.tools import materialize
from squadron.tools.builtin import GREP_NAME, LIST_FILES_NAME

_SECRET = "SUPERSECRET_OUTSIDE_JAIL"


@pytest.fixture
def jail_with_escape(tmp_path: Path) -> tuple[Path, Path]:
    """A jail containing a symlinked file and a symlinked directory, both pointing out."""
    jail = tmp_path / "jail"
    outside = tmp_path / "outside"
    (jail / "sub").mkdir(parents=True)
    outside.mkdir()
    (outside / "loot.txt").write_text(f"{_SECRET}\n")
    (jail / "inside.txt").write_text("ordinary jail content\n")
    (jail / "link_to_file.txt").symlink_to(outside / "loot.txt")
    (jail / "link_to_dir").symlink_to(outside, target_is_directory=True)
    return jail, outside


async def _run(tool_name: str, jail: Path, args: dict[str, object]) -> str:
    executor = materialize([tool_name], str(jail))[tool_name]
    result = await executor(args)
    return result.content


@pytest.mark.asyncio
async def test_grep_refuses_symlinked_file(
    jail_with_escape: tuple[Path, Path], caplog: pytest.LogCaptureFixture
) -> None:
    """SC5: a symlinked file whose target is outside the jail yields no content."""
    jail, _ = jail_with_escape
    with caplog.at_level(logging.WARNING, logger="squadron.tools.builtin"):
        content = await _run(GREP_NAME, jail, {"pattern": _SECRET})

    assert _SECRET not in content
    assert any(GREP_NAME in r.message and "jail escape" in r.message for r in caplog.records), (
        "the containment guard was never reached — this test would pass vacuously"
    )


@pytest.mark.asyncio
async def test_grep_refuses_symlinked_directory(
    jail_with_escape: tuple[Path, Path], caplog: pytest.LogCaptureFixture
) -> None:
    """SC5, the version-dependent case: assert on the guard, not just absent output."""
    jail, _ = jail_with_escape
    # Remove the file link so only the directory link can trip the guard.
    (jail / "link_to_file.txt").unlink()

    with caplog.at_level(logging.WARNING, logger="squadron.tools.builtin"):
        content = await _run(GREP_NAME, jail, {"pattern": _SECRET})

    assert _SECRET not in content
    assert any(GREP_NAME in r.message and "jail escape" in r.message for r in caplog.records), (
        "the containment guard was never reached — this test would pass vacuously"
    )


@pytest.mark.asyncio
async def test_list_files_refuses_symlinked_file(
    jail_with_escape: tuple[Path, Path], caplog: pytest.LogCaptureFixture
) -> None:
    """SC6: list_files must not name an entry resolving outside the jail."""
    jail, _ = jail_with_escape
    with caplog.at_level(logging.WARNING, logger="squadron.tools.builtin"):
        content = await _run(LIST_FILES_NAME, jail, {"path": ".", "recursive": True})

    assert "link_to_file.txt" not in content
    # The ordinary jail content is still listed — the guard is not a blanket refusal.
    assert "inside.txt" in content
    assert any(LIST_FILES_NAME in r.message and "jail escape" in r.message for r in caplog.records), (
        "the containment guard was never reached — this test would pass vacuously"
    )


@pytest.mark.asyncio
async def test_list_files_refuses_symlinked_directory(
    jail_with_escape: tuple[Path, Path], caplog: pytest.LogCaptureFixture
) -> None:
    """SC6, the version-dependent case."""
    jail, _ = jail_with_escape
    (jail / "link_to_file.txt").unlink()

    with caplog.at_level(logging.WARNING, logger="squadron.tools.builtin"):
        content = await _run(LIST_FILES_NAME, jail, {"path": ".", "recursive": True})

    assert "link_to_dir" not in content
    assert "loot.txt" not in content
    assert any(LIST_FILES_NAME in r.message and "jail escape" in r.message for r in caplog.records), (
        "the containment guard was never reached — this test would pass vacuously"
    )


@pytest.mark.asyncio
async def test_ordinary_jail_content_is_unaffected(jail_with_escape: tuple[Path, Path]) -> None:
    """The guard must not refuse legitimate entries — the regression it could cause."""
    jail, _ = jail_with_escape
    (jail / "sub" / "deep.txt").write_text("findme in a subdirectory\n")

    listing = await _run(LIST_FILES_NAME, jail, {"path": ".", "recursive": True})
    assert "inside.txt" in listing
    assert "sub/deep.txt" in listing

    grepped = await _run(GREP_NAME, jail, {"pattern": "findme"})
    assert "deep.txt" in grepped
