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

# Maximum directory entries ``list_files`` will walk. Bounds the *work*: without it a wide
# tree is fully materialized by ``sorted()`` before the byte-level output cap ever applies,
# so a large enough tree costs the full walk no matter how little is returned. Distinct from
# MAX_OUTPUT_BYTES, which bounds the rendered listing; both apply.
MAX_LIST_ENTRIES = 10_000

# Maximum characters of a single tool result admitted into agent history. Applied per
# result, before the append: the whole-conversation ``agent.max_history_chars`` guard is a
# backstop, and one oversized result must not be able to exhaust it on its own.
MAX_TOOL_RESULT_CHARS = 100_000

# Maximum length of a model-supplied ``grep`` pattern. Checked before compilation: the
# point is to never hand an unbounded pattern to the regex engine at all, since compilation
# itself is where a pathological pattern does its damage.
MAX_PATTERN_CHARS = 1_000

# Wall-clock seconds the ``grep`` tool's regex matching may consume across an entire
# walk before the search is abandoned. Bounds catastrophic backtracking on
# model-supplied patterns; the ``regex`` package enforces it at the engine level.
GREP_TIMEOUT_S = 5.0
