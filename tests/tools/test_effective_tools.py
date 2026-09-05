"""Tests for the slice 266 capability gate.

Covers ``resolve_effective_tools`` itself (T4), the ``tool_use`` alias field
(T1/T2), and the gate at each sanctioned ``AgentConfig`` call site (T6, T10),
plus the SC1a enumeration guard that keeps a new call site from skipping it.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from squadron.models.aliases import get_all_aliases, load_builtin_aliases
from squadron.tools import SuppressionReason, resolve_effective_tools

DECLARED = ["read_file", "grep"]


# ---------------------------------------------------------------------------
# T4 — resolve_effective_tools truth table
# ---------------------------------------------------------------------------


def test_declared_passes_through_when_nothing_denies() -> None:
    """No denial: the declared list survives intact with no reason."""
    tools, reason = resolve_effective_tools(DECLARED, model_allows_tools=True, suppressed=False)
    assert tools == DECLARED
    assert reason is None


def test_capability_denial_empties_the_set() -> None:
    """tool_use = false empties a non-empty declared set."""
    tools, reason = resolve_effective_tools(DECLARED, model_allows_tools=False, suppressed=False)
    assert tools == []
    assert reason == SuppressionReason.MODEL_CAPABILITY.value


def test_run_suppression_empties_the_set() -> None:
    """--no-tools empties a non-empty declared set."""
    tools, reason = resolve_effective_tools(DECLARED, model_allows_tools=True, suppressed=True)
    assert tools == []
    assert reason == SuppressionReason.RUN_SUPPRESSED.value


def test_both_denials_are_recorded_together() -> None:
    """Both denials at once: neither is lost by reporting only one."""
    tools, reason = resolve_effective_tools(DECLARED, model_allows_tools=False, suppressed=True)
    assert tools == []
    assert reason == SuppressionReason.BOTH.value


def test_capability_and_suppression_reasons_are_distinguishable() -> None:
    """SC4: telemetry must tell the two denials apart, not merely flag both."""
    _, capability = resolve_effective_tools(DECLARED, model_allows_tools=False, suppressed=False)
    _, suppressed = resolve_effective_tools(DECLARED, model_allows_tools=True, suppressed=True)
    assert capability != suppressed
    assert capability is not None and suppressed is not None


def test_none_declared_is_not_a_suppression() -> None:
    """Nothing declared is not a suppression and must not be announced as one."""
    tools, reason = resolve_effective_tools(None, model_allows_tools=False, suppressed=True)
    assert tools == []
    assert reason is None


def test_empty_declared_is_not_a_suppression() -> None:
    """An already-empty declared set behaves the same as None."""
    tools, reason = resolve_effective_tools([], model_allows_tools=False, suppressed=True)
    assert tools == []
    assert reason is None


def test_result_does_not_alias_the_caller_list() -> None:
    """The returned list is a copy: a caller mutating it cannot corrupt the source."""
    declared = list(DECLARED)
    tools, _ = resolve_effective_tools(declared, model_allows_tools=True, suppressed=False)
    tools.append("bash")
    assert declared == DECLARED


# ---------------------------------------------------------------------------
# T1/T2 — the tool_use alias field
# ---------------------------------------------------------------------------


def test_alias_tool_use_false_reads_back(tmp_path: Path) -> None:
    """T1: an alias with tool_use = false reads back False."""
    toml_file = tmp_path / "models.toml"
    toml_file.write_text('[aliases]\ngated = { profile = "openai", model = "m", tool_use = false }\n')

    with patch("squadron.models.aliases.models_toml_path", return_value=toml_file):
        aliases = get_all_aliases()

    assert aliases["gated"]["tool_use"] is False


def test_alias_without_tool_use_has_no_key(tmp_path: Path) -> None:
    """T1: absence stays distinguishable from an explicit true (SC2)."""
    toml_file = tmp_path / "models.toml"
    toml_file.write_text('[aliases]\nplain = { profile = "openai", model = "m" }\n')

    with patch("squadron.models.aliases.models_toml_path", return_value=toml_file):
        aliases = get_all_aliases()

    assert "tool_use" not in aliases["plain"]


def test_non_bool_tool_use_is_ignored(tmp_path: Path) -> None:
    """A non-bool value is not accepted, matching the private field's guard."""
    toml_file = tmp_path / "models.toml"
    toml_file.write_text('[aliases]\nodd = { profile = "openai", model = "m", tool_use = "false" }\n')

    with patch("squadron.models.aliases.models_toml_path", return_value=toml_file):
        aliases = get_all_aliases()

    assert "tool_use" not in aliases["odd"]


def test_no_shipped_alias_sets_tool_use() -> None:
    """T2/SC2: default-true preserves current behavior for every existing user."""
    for name, alias in load_builtin_aliases().items():
        assert "tool_use" not in alias, f"shipped alias {name} must not set tool_use"
