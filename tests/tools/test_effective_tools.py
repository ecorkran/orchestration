"""Tests for the slice 266 capability gate.

Covers ``resolve_effective_tools`` itself (T4), the ``tool_use`` alias field
(T1/T2), and the gate at each sanctioned ``AgentConfig`` call site (T6, T10),
plus the SC1a enumeration guard that keeps a new call site from skipping it.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from squadron.core.models import AgentConfig, AgentState, Message, MessageType
from squadron.models.aliases import get_all_aliases, load_builtin_aliases
from squadron.providers.base import ProviderCapabilities
from squadron.providers.profiles import ProviderProfile
from squadron.review.models import ReviewResult
from squadron.review.review_client import run_review_with_profile
from squadron.review.templates import ReviewTemplate
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


# ---------------------------------------------------------------------------
# T6 — the gate on the review-client path (SC1, SC2, SC4)
#
# This task owns the review-client case. T10 below covers the other three
# sanctioned sites and must not restate it.
# ---------------------------------------------------------------------------

_P = "squadron.review.review_client"

_SAMPLE_REVIEW_OUTPUT = """\
**Verdict:** PASS

## Findings

### [PASS] — Looks fine

Nothing to report.
"""


def _make_template(allowed_tools: list[str] | None) -> ReviewTemplate:
    return ReviewTemplate(
        name="test",
        description="Test template",
        system_prompt="You are a reviewer.",
        allowed_tools=allowed_tools,
        permission_mode="bypassPermissions",
        setting_sources=None,
        required_inputs=[],
        optional_inputs=[],
        prompt_template="Review: {input}",
        profile=None,
        model=None,
    )


def _capture_provider(captured: dict[str, AgentConfig]) -> MagicMock:
    """A mock provider recording the AgentConfig its agent was built from."""
    agent = MagicMock()
    agent.state = AgentState.idle
    agent.shutdown = AsyncMock()

    async def _handle(message: Message) -> AsyncIterator[Message]:
        yield Message(
            sender="mock-agent",
            recipients=[],
            content=_SAMPLE_REVIEW_OUTPUT,
            message_type=MessageType.chat,
        )

    agent.handle_message = _handle

    async def _create_agent(config: AgentConfig) -> MagicMock:
        captured["config"] = config
        return agent

    provider = MagicMock()
    provider.capabilities = ProviderCapabilities(can_read_files=False)
    provider.create_agent = _create_agent
    return provider


async def _run_review(
    tmp_path: Path,
    *,
    allowed_tools: list[str] | None,
    model: str | None,
    aliases_toml: str,
    no_tools: bool = False,
) -> tuple[AgentConfig, ReviewResult]:
    target = tmp_path / "design.md"
    target.write_text("SENTINEL FILE BODY")
    toml_file = tmp_path / "models.toml"
    toml_file.write_text(aliases_toml)

    captured: dict[str, AgentConfig] = {}
    provider = _capture_provider(captured)
    profile = ProviderProfile(name="openai", provider="openai", api_key_env="OPENAI_API_KEY")

    with (
        patch(f"{_P}.get_profile", return_value=profile),
        patch(f"{_P}.get_provider", return_value=provider),
        patch(f"{_P}.ensure_provider_loaded"),
        patch("squadron.models.aliases.models_toml_path", return_value=toml_file),
    ):
        result = await run_review_with_profile(
            _make_template(allowed_tools),
            {"input": str(target), "cwd": str(tmp_path)},
            profile=profile.name,
            model=model,
            no_tools=no_tools,
        )
    return captured["config"], result


_GATED_TOML = '[aliases]\ngated = { profile = "openai", model = "m", tool_use = false }\n'
_PLAIN_TOML = '[aliases]\nplain = { profile = "openai", model = "m" }\n'


@pytest.mark.asyncio
async def test_review_gate_empties_tools_for_denied_model(tmp_path: Path) -> None:
    """SC1: a tool_use = false model gets no tools even though the template declares them."""
    config, result = await _run_review(
        tmp_path,
        allowed_tools=["read_file", "grep"],
        model="gated",
        aliases_toml=_GATED_TOML,
    )
    assert config.allowed_tools == []
    assert config.tools_suppressed_reason == SuppressionReason.MODEL_CAPABILITY.value
    assert result.tools_suppressed_reason == SuppressionReason.MODEL_CAPABILITY.value


@pytest.mark.asyncio
async def test_review_gate_passes_tools_when_field_absent(tmp_path: Path) -> None:
    """SC2: an alias without tool_use is unaffected — the default-allow case."""
    config, result = await _run_review(
        tmp_path,
        allowed_tools=["read_file", "grep"],
        model="plain",
        aliases_toml=_PLAIN_TOML,
    )
    assert config.allowed_tools == ["read_file", "grep"]
    assert config.tools_suppressed_reason is None
    assert result.tools_suppressed_reason is None


@pytest.mark.asyncio
async def test_review_gate_logs_on_suppression(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """SC4: suppression is announced at INFO."""
    with caplog.at_level(logging.INFO, logger="squadron.review.review_client"):
        await _run_review(
            tmp_path,
            allowed_tools=["read_file"],
            model="gated",
            aliases_toml=_GATED_TOML,
        )
    assert any("suppressed" in record.message.lower() for record in caplog.records)


@pytest.mark.asyncio
async def test_review_gate_silent_when_nothing_declared(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A template declaring no tools is not a suppression and must not be announced."""
    with caplog.at_level(logging.INFO, logger="squadron.review.review_client"):
        config, result = await _run_review(
            tmp_path,
            allowed_tools=None,
            model="gated",
            aliases_toml=_GATED_TOML,
        )
    assert config.tools_suppressed_reason is None
    assert result.tools_suppressed_reason is None
    assert not any("suppressed" in record.message.lower() for record in caplog.records)
