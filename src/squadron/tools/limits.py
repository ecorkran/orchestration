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
# apart. A fixed 100_000 against the old 400_000 default let one result take a quarter of the
# budget, so four full-size results exhausted it — an observed review made 45 tool calls and
# was forced to finalize early (issue #80).
#
# The fraction alone was not enough. A tool result is bounded by MAX_OUTPUT_BYTES (64_000),
# so a budget of 400_000 admits only ~6 full-size results however the cap is computed; the
# budget itself was the binding constraint and is now 1_000_000. Note the interaction: this
# fraction can only *raise* the cap above the headroom floor below, never lower it.
TOOL_RESULT_HISTORY_FRACTION = 0.05

# Headroom the per-result cap keeps above the largest result a well-behaved tool can
# return. Every built-in tool already bounds its own output at MAX_OUTPUT_BYTES and appends
# a marker saying so; the agent-side cap is a backstop for a tool that does not, so it must
# sit *above* that bound. Setting it lower re-truncates ordinary results, replacing the
# tool's own "showing first N" marker with a cut mid-line — which is what turned a working
# review into one usable tool call and an UNKNOWN verdict.
TOOL_RESULT_HEADROOM = 1.5


def max_tool_result_chars(max_history_chars: int) -> int:
    """Return the per-result character cap for a given history budget.

    Never returns less than ``MAX_OUTPUT_BYTES * TOOL_RESULT_HEADROOM``: below that the cap
    stops being a backstop and starts mangling results the tools already truncated
    correctly. Read at call time, never captured at import, so tests can monkeypatch any
    input and the executor sees the change.
    """
    floor = int(MAX_OUTPUT_BYTES * TOOL_RESULT_HEADROOM)
    return max(floor, int(max_history_chars * TOOL_RESULT_HISTORY_FRACTION))


# Maximum length of a model-supplied ``grep`` pattern. Checked before compilation: the
# point is to never hand an unbounded pattern to the regex engine at all, since compilation
# itself is where a pathological pattern does its damage.
MAX_PATTERN_CHARS = 1_000

# Wall-clock seconds the ``grep`` tool's regex matching may consume across an entire
# walk before the search is abandoned. Bounds catastrophic backtracking on
# model-supplied patterns; the ``regex`` package enforces it at the engine level.
GREP_TIMEOUT_S = 5.0
