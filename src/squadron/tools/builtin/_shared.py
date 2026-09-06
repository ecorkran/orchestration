"""Shared helpers for the built-in tools: the path jail, error results, and argument
coercion.

Split out of the former single-module ``builtin.py`` (slice 266, T23). Pure move — no
logic changed."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path

from squadron.tools import limits
from squadron.tools.models import ToolResult

# Canonical tool names. Defined once here and referenced everywhere else.
READ_FILE_NAME = "read_file"
WRITE_FILE_NAME = "write_file"
BASH_NAME = "bash"
LIST_FILES_NAME = "list_files"
GREP_NAME = "grep"

_logger = logging.getLogger(__name__)


def resolve_in_jail(cwd: Path, path: str) -> Path | None:
    """Resolve model-supplied *path* against jail root *cwd*, or return None if it escapes.

    ``cwd / path`` covers relative inputs, absolute inputs (``Path.__truediv__`` with an
    absolute right-hand operand yields that absolute path), and ``..`` traversal in one
    expression. ``resolve()`` follows symlinks first, so a link whose target lies outside the
    jail is rejected too.

    String prefix comparison is deliberately not used: it is wrong across path-component
    boundaries (``/tmp/jail_evil`` starts with ``/tmp/jail`` but is not inside it).
    """
    candidate = (cwd / path).resolve(strict=False)
    if not candidate.is_relative_to(cwd):
        return None
    return candidate


def contained_in_jail(cwd: Path, entry: Path, *, tool: str) -> bool:
    """Return whether *entry* really lies inside jail root *cwd*, logging refusals.

    A walk yields entries that were never checked against the jail: ``Path.is_file()``
    follows symlinks, so a link inside the jail pointing outside it looks like an ordinary
    file, and on Python <= 3.12 ``rglob`` also recurses *into* symlinked directories.
    Re-resolving each candidate closes both routes at the point candidates are produced.

    The refusal is silent to the model (design D6) — a skipped entry is indistinguishable
    from one that did not match, whereas "you were denied" invites probing for the jail
    boundary. It is logged at WARNING so the refusal is observable to an operator.
    """
    resolved = entry.resolve(strict=False)
    if resolved.is_relative_to(cwd):
        return True
    _logger.warning("%s: refusing jail escape via %s -> %s (outside %s)", tool, entry, resolved, cwd)
    return False


def walk_tree(root: Path, *, recursive: bool = True) -> Iterator[Path]:
    """Yield entries under *root*, pruning ``limits.SKIP_DIRECTORIES`` as it descends.

    ``Path.rglob`` cannot prune: it yields every entry, so a caller filtering afterwards has
    already paid to stat everything under ``.venv`` or ``node_modules``. That cost, not
    regex backtracking, is what exhausted the ``grep`` budget in practice (issue #79).

    Pruning is by exact directory name at any depth, and applies to *descent* only — a
    caller that explicitly asks for ``.venv`` as its root still gets it, since the skip set
    is consulted for children rather than for *root* itself.

    Lazy by construction. Nothing here materializes the tree; the budget and entry caps
    upstream depend on being able to stop early.
    """
    skip = limits.SKIP_DIRECTORIES
    try:
        entries = sorted(root.iterdir())
    except (OSError, PermissionError):
        # An unreadable directory inside the tree is normal input for a whole-tree walk;
        # the remaining entries are still worth yielding.
        return
    for entry in entries:
        yield entry
        if not recursive:
            continue
        if entry.name in skip:
            _logger.debug("walk: pruning %s", entry)
            continue
        # is_dir() follows symlinks; descending through one is how a walk leaves the jail,
        # so links are yielded above (the caller's containment check sees them) but never
        # descended into.
        if entry.is_dir() and not entry.is_symlink():
            yield from walk_tree(entry, recursive=True)


def reject_special_file(tool: str, target: Path) -> ToolResult | None:
    """Return an error result if *target* exists and is not a regular file, else None.

    A read or write against a FIFO, device node, or socket blocks in the thread pool with no
    way to cancel it — unlike ``bash``, which can kill its subprocess. ``asyncio.to_thread``
    workers are not interruptible, so a caller-side ``wait_for`` does not rescue the process
    either: the interpreter joins the stuck thread at shutdown and hangs anyway. The jail
    admits any path under the working directory, so a special file inside it is realistic
    input, not a hypothetical. The only reliable defense is to refuse before opening.

    Directories are deliberately not rejected here — the file tools report those with their own
    specific messages.
    """
    if not target.exists() or target.is_dir():
        return None
    if not target.is_file():
        return error(tool, f"path is not a regular file: {target.name}")
    return None


def jail_violation(tool: str, path: str) -> ToolResult:
    """Build the error result for a rejected path and log it at WARNING.

    The working directory is the trust boundary, so an escape attempt must be visible without
    raising verbosity.
    """
    _logger.warning("%s: rejected path outside working directory: %s", tool, path)
    return ToolResult(
        content=f"Error: path '{path}' resolves outside the working directory and was rejected.",
        is_error=True,
    )


def error(tool: str, message: str) -> ToolResult:
    """Build a routine error result and log it at INFO.

    These are outcomes the model probes for and reacts to — a missing file, a permission
    denial, a non-zero exit. Elevating them to WARNING would train operators to ignore
    warnings.
    """
    _logger.info("%s: %s", tool, message)
    return ToolResult(content=f"Error: {message}", is_error=True)


async def guarded(tool: str, run: Callable[[], Awaitable[ToolResult]]) -> ToolResult:
    """Run *run*, converting expected failures into error results.

    Every executor routes through this wrapper. From slice 262 onward the caller is a model
    loop, so an unexpected tool bug must surface as an observable error result rather than
    crash the run — hence the catch-all, which is a process-boundary handler.
    """
    try:
        return await run()
    except FileNotFoundError as exc:
        return error(tool, f"file not found: {exc.filename or exc}")
    except IsADirectoryError as exc:
        return error(tool, f"path is a directory: {exc.filename or exc}")
    except NotADirectoryError as exc:
        return error(tool, f"path component is not a directory: {exc.filename or exc}")
    except PermissionError as exc:
        return error(tool, f"permission denied: {exc.filename or exc}")
    except UnicodeDecodeError as exc:
        return error(tool, f"could not decode content: {exc}")
    except TimeoutError as exc:
        return error(tool, f"operation timed out: {exc}")
    except Exception as exc:  # noqa: BLE001
        _logger.exception("%s: unexpected failure", tool)
        return ToolResult(content=f"Error: unexpected failure in {tool}: {exc}", is_error=True)


def require_str(args: dict[str, object], key: str) -> str:
    """Return ``args[key]`` as a string, or raise ValueError describing what was wrong.

    Arguments arrive from a model and are untyped by construction, so they are narrowed at the
    boundary rather than indexed and passed blind.
    """
    if key not in args:
        raise ValueError(f"missing required argument '{key}'")
    value = args[key]
    if not isinstance(value, str):
        raise ValueError(f"argument '{key}' must be a string, got {type(value).__name__}")
    return value


def truncate(data: bytes, limit: int, label: str) -> str:
    """Decode *data*, truncating to *limit* bytes with a visible trailing marker.

    Truncation is never silent: the model has to know it did not see everything. Decoding
    after the byte-level cut with ``errors="replace"`` also absorbs a split codepoint at the
    boundary.
    """
    if len(data) <= limit:
        return data.decode(errors="replace")
    kept = data[:limit].decode(errors="replace")
    return f"{kept}\n[truncated: {label} is {len(data)} bytes, showing first {limit}]"


def optional_str(args: dict[str, object], key: str, default: str) -> str:
    """Return ``args[key]`` as a string, falling back to *default* when absent or null.

    Same boundary-narrowing rationale as ``require_str``: model-supplied arguments are
    untyped, and an optional argument that arrives with the wrong type is a caller error the
    model can correct, not something to coerce silently.
    """
    value = args.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"argument '{key}' must be a string, got {type(value).__name__}")
    return value


def optional_bool(args: dict[str, object], key: str, default: bool) -> bool:
    """Return ``args[key]`` as a bool, falling back to *default* when absent or null."""
    value = args.get(key)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"argument '{key}' must be a boolean, got {type(value).__name__}")
    return value


def format_entry(entry: Path, root: Path) -> str:
    """Render *entry* relative to jail root *root*, marking directories with a trailing slash."""
    rendered = str(entry.relative_to(root))
    return f"{rendered}/" if entry.is_dir() else rendered


def optional_int(args: dict[str, object], key: str) -> int | None:
    """Return ``args[key]`` as an int, or None when absent or null.

    ``bool`` is rejected explicitly: it is a subclass of ``int``, so a model passing ``true``
    would otherwise silently become a cap of 1.
    """
    value = args.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"argument '{key}' must be an integer, got {type(value).__name__}")
    return value
