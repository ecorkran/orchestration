"""Guard: every text-mode ``subprocess.run`` pins UTF-8 decoding (issue #63).

``text=True`` alone decodes with the locale codec, which is cp1252 on
Windows; a non-ASCII byte in git output then raises ``UnicodeDecodeError``
before the model is reached. The fix is ``**TEXT_DECODING`` on every such
call. This test walks the AST of the package so a new call site cannot
silently reintroduce the locale dependence.
"""

from __future__ import annotations

import ast
from pathlib import Path

import squadron
from squadron.core.subprocess_text import TEXT_DECODING

_SRC_ROOT = Path(squadron.__file__).parent


def _is_subprocess_run(call: ast.Call) -> bool:
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "run"
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    )


def _text_mode_without_pin(call: ast.Call) -> bool:
    text_mode = any(
        kw.arg == "text" and isinstance(kw.value, ast.Constant) and kw.value.value is True
        for kw in call.keywords
    )
    pinned = any(
        kw.arg is None and isinstance(kw.value, ast.Name) and kw.value.id == "TEXT_DECODING"
        for kw in call.keywords
    )
    return text_mode and not pinned


def test_text_decoding_pins_utf8() -> None:
    assert TEXT_DECODING == {"encoding": "utf-8", "errors": "replace"}


def test_every_text_mode_subprocess_run_passes_text_decoding() -> None:
    offenders: list[str] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_subprocess_run(node) and _text_mode_without_pin(node):
                offenders.append(f"{path.relative_to(_SRC_ROOT.parent)}:{node.lineno}")
    assert not offenders, "subprocess.run(text=True) without **TEXT_DECODING:\n" + "\n".join(offenders)
