"""Single home for tool execution limits.

Every limit enforced by a built-in tool is defined here and nowhere else. Tool
implementations reference these constants by module attribute (``limits.MAX_READ_BYTES``)
rather than importing the values, so tests can monkeypatch them and the executor sees the
patched value at call time.

Slice 266 considered making these configurable and decided against it (design D4): they
stay module attributes with no config keys until someone actually needs to tune one. A
config surface for values nobody has had to change would be plumbing maintained for its
own sake, and it would split each limit's definition across two places.

The decision is settled, not deferred. If a limit does need tuning, the constraints any
config surface must preserve are recorded in
https://github.com/ecorkran/squadron/issues/76 — chiefly that a constant must resolve
*from* config rather than sit beside it, or this module stops being one home for a value.
"""

from __future__ import annotations

# Maximum number of bytes ``read_file`` returns before truncating with a visible marker.
MAX_READ_BYTES = 256_000

# Maximum number of bytes of each captured stream (stdout, stderr) ``bash`` returns.
MAX_OUTPUT_BYTES = 64_000

# Wall-clock seconds a ``bash`` command may run before its process group is killed.
BASH_TIMEOUT_S = 120.0

# Directory names the walking tools prune by default. These hold dependencies, VCS
# internals, and build output — not the code a model is asked about — and they dominate a
# real tree: in this repo ``.venv`` alone is 21,402 of 29,373 entries, and reading it
# exhausts the whole ``grep`` budget before any project file is reached (issue #79).
#
# Pruned at the directory level during the walk, so their contents are never stat-ed or
# opened. Matched by exact directory name at any depth. A caller that genuinely wants to
# search inside one names it in ``path`` — the prune applies to descent, not to an
# explicitly requested root.
SKIP_DIRECTORIES = frozenset(
    {
        ".bzr",
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
)

# Maximum directory entries ``list_files`` will walk. Bounds the *work*: without it a wide
# tree is fully materialized by ``sorted()`` before the byte-level output cap ever applies,
# so a large enough tree costs the full walk no matter how little is returned. Distinct from
# MAX_OUTPUT_BYTES, which bounds the rendered listing; both apply.
MAX_LIST_ENTRIES = 10_000

# Share of the conversation history budget a *single* tool result may occupy. Applied per
# result, before the append: the whole-conversation ``agent.max_history_chars`` guard is a
# backstop, and one oversized result must not be able to exhaust it on its own.
#
# Expressed as a fraction rather than a fixed character count so the two limits cannot drift
# apart. A fixed 100_000 against the 400_000 default let one result take a quarter of the
# budget, so four full-size results exhausted it — an observed review made 45 tool calls and
# was forced to finalize early (issue #80). At 5% a run has room for ~20 maximum-size
# results, and raising ``agent.max_history_chars`` now raises this with it.
TOOL_RESULT_HISTORY_FRACTION = 0.05

# Floor for the derived per-result cap, so a small configured history budget cannot shrink
# tool results to uselessness — a result too short to carry a file's relevant span makes the
# tool worse than not having it.
MIN_TOOL_RESULT_CHARS = 4_000


def max_tool_result_chars(max_history_chars: int) -> int:
    """Return the per-result character cap for a given history budget.

    Read at call time, never captured at import, so tests can monkeypatch either input and
    the executor sees the change.
    """
    return max(MIN_TOOL_RESULT_CHARS, int(max_history_chars * TOOL_RESULT_HISTORY_FRACTION))


# Maximum length of a model-supplied ``grep`` pattern. Checked before compilation: the
# point is to never hand an unbounded pattern to the regex engine at all, since compilation
# itself is where a pathological pattern does its damage.
MAX_PATTERN_CHARS = 1_000

# Wall-clock seconds the ``grep`` tool's regex matching may consume across an entire
# walk before the search is abandoned. Bounds catastrophic backtracking on
# model-supplied patterns; the ``regex`` package enforces it at the engine level.
GREP_TIMEOUT_S = 5.0
