"""The capability gate: resolves which tools a run may actually offer.

Slice 266. Every ``AgentConfig`` construction that sets ``allowed_tools`` routes
its declared list through :func:`resolve_effective_tools` first. The agent
cannot do this itself — it receives an already-resolved model id and must not
read models.toml (slice 266 design, D3), so it materializes whatever list it is
handed and cannot tell a gated list from an un-gated one.

There is consequently no structural chokepoint, and the enumeration test
(SC1a, ``tests/tools/test_effective_tools.py``) is what keeps a new call site
from quietly skipping the gate.
"""

from __future__ import annotations

from enum import StrEnum


class SuppressionReason(StrEnum):
    """Why an effective tool set was emptied.

    The values are persisted into review artifacts and read by operators, so
    they are prose-stable identifiers rather than free text: SC4 requires
    capability-denial and run-level suppression to be told apart from the
    recorded field alone, never by interpreting model output.
    """

    MODEL_CAPABILITY = "model-capability"
    """The alias sets ``tool_use = false`` — the model never gets tool schemas."""

    RUN_SUPPRESSED = "run-suppressed"
    """This one run asked for no tools, e.g. ``sq review ... --no-tools``."""

    BOTH = "model-capability+run-suppressed"
    """Both denials applied; recorded so neither is lost by reporting only one."""


def resolve_effective_tools(
    declared: list[str] | None,
    *,
    model_allows_tools: bool,
    suppressed: bool,
) -> tuple[list[str], str | None]:
    """Return the tools a run may offer, and why the set was emptied.

    ``declared`` is what the caller wanted to offer — a template's tool list, a
    pipeline step's, or a fixed module constant. The effective set is that list
    narrowed by the model's ``tool_use`` capability and by run-level
    suppression; either denial empties it entirely.

    The second element is a :class:`SuppressionReason` value when a non-empty
    declared set was emptied, and ``None`` otherwise. An empty or ``None``
    ``declared`` yields ``([], None)``: nothing was declared, which is not a
    suppression and must not be announced as one.
    """
    if not declared:
        return [], None

    if not model_allows_tools and suppressed:
        return [], SuppressionReason.BOTH.value
    if not model_allows_tools:
        return [], SuppressionReason.MODEL_CAPABILITY.value
    if suppressed:
        return [], SuppressionReason.RUN_SUPPRESSED.value

    return list(declared), None
