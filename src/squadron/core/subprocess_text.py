"""Text decoding for child-process output.

``subprocess.run(text=True)`` decodes stdout/stderr with the locale codec —
cp1252 on Windows — while git, ``cf`` and npm emit UTF-8 on every platform.
An em dash in a diff was enough to raise ``UnicodeDecodeError`` before the
review model was reached (issue #63). Every text-mode subprocess call passes
``**TEXT_DECODING`` so the pin is defined in exactly one place.
"""

from __future__ import annotations

from typing import Final, TypedDict


class TextDecoding(TypedDict):
    """Keyword arguments that fix how ``subprocess`` decodes child output."""

    encoding: str
    errors: str


#: Git and the other CLIs squadron shells out to write UTF-8 regardless of the
#: host locale. ``errors="replace"`` keeps a stray invalid byte from aborting
#: an otherwise-usable diff.
TEXT_DECODING: Final[TextDecoding] = {"encoding": "utf-8", "errors": "replace"}
