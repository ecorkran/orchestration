"""Single home for tool execution limits.

Every limit enforced by a built-in tool is defined here and nowhere else. Tool
implementations reference these constants by module attribute (``limits.MAX_READ_BYTES``)
rather than importing the values, so tests can monkeypatch them and the executor sees the
patched value at call time.

Making these configurable is slice 266's job — this module deliberately has no config
plumbing.
"""

from __future__ import annotations

# Maximum number of bytes ``read_file`` returns before truncating with a visible marker.
MAX_READ_BYTES = 256_000

# Maximum number of bytes of each captured stream (stdout, stderr) ``bash`` returns.
MAX_OUTPUT_BYTES = 64_000

# Wall-clock seconds a ``bash`` command may run before its process group is killed.
BASH_TIMEOUT_S = 120.0

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
