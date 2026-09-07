"""Tests for the run-scoped file-body injection decision (slice 265, design D1).

The decision used to read ``ProviderCapabilities.can_read_files`` alone — a per-provider
constant blind to what a given run was actually given. These tests cover the helper directly
and, end to end, assert what reaches the model's prompt.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from squadron.core.models import AgentState, Message, MessageType
from squadron.providers.base import AuthType, ProfileName, ProviderCapabilities, ProviderType
from squadron.providers.profiles import ProviderProfile
from squadron.review.review_client import run_review_with_profile
from squadron.review.templates import ReviewTemplate
from squadron.review.tool_support import effective_tools, should_inject_file_bodies

_P = "squadron.review.review_client"

_SAMPLE_REVIEW_OUTPUT = """\
**Verdict:** PASS

## Findings

### [PASS] — Looks fine

Nothing to report.
"""


# ---------------------------------------------------------------------------
# effective_tools / should_inject_file_bodies — unit level
# ---------------------------------------------------------------------------


def test_effective_tools_filters_unregistered_names_for_non_sdk() -> None:
    assert effective_tools(["read_file", "Read", "grep"], "openai") == ["read_file", "grep"]


def test_effective_tools_passes_sdk_names_through_untouched() -> None:
    # SDK profiles resolve their own vocabulary at the config edge, so nothing is filtered.
    assert effective_tools(["Read", "Glob"], ProviderType.SDK) == ["Read", "Glob"]


def test_effective_tools_empty_for_no_declaration() -> None:
    assert effective_tools(None, "openai") == []
    assert effective_tools([], "openai") == []


def test_reader_tool_suppresses_injection() -> None:
    assert (
        should_inject_file_bodies(
            can_read_files=False, allowed_tools=["read_file", "grep"], provider="openai"
        )
        is False
    )


def test_no_reader_tool_still_injects() -> None:
    assert (
        should_inject_file_bodies(can_read_files=False, allowed_tools=["grep"], provider="openai")
        is True
    )


def test_no_tools_declared_still_injects() -> None:
    assert (
        should_inject_file_bodies(can_read_files=False, allowed_tools=None, provider="openai") is True
    )


def test_native_reader_never_injects_regardless_of_tools() -> None:
    for tools in (None, [], ["read_file"], ["Read"]):
        assert (
            should_inject_file_bodies(
                can_read_files=True, allowed_tools=tools, provider=ProviderType.SDK
            )
            is False
        )


def test_unregistered_reader_name_does_not_suppress_injection() -> None:
    # A template still declaring Claude vocabulary against a non-SDK provider has no effective
    # reader, so bodies must still be injected — the pre-migration regression case.
    assert (
        should_inject_file_bodies(can_read_files=False, allowed_tools=["Read"], provider="openai")
        is True
    )


# ---------------------------------------------------------------------------
# End to end — what actually reaches the prompt
# ---------------------------------------------------------------------------


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


def _capture_provider(captured: dict[str, str], *, can_read_files: bool) -> MagicMock:
    """A mock provider that records the user prompt its agent receives."""
    agent = MagicMock()
    agent.state = AgentState.idle
    agent.shutdown = AsyncMock()

    async def _handle(message: Message) -> AsyncIterator[Message]:
        captured["prompt"] = message.content
        yield Message(
            sender="mock-agent",
            recipients=[],
            content=_SAMPLE_REVIEW_OUTPUT,
            message_type=MessageType.chat,
        )

    agent.handle_message = _handle
    provider = MagicMock()
    provider.capabilities = ProviderCapabilities(can_read_files=can_read_files)
    provider.create_agent = AsyncMock(return_value=agent)
    return provider


async def _run(tmp_path: Path, *, allowed_tools: list[str] | None, sdk: bool) -> str:
    target = tmp_path / "design.md"
    target.write_text("SENTINEL FILE BODY")
    captured: dict[str, str] = {}
    provider = _capture_provider(captured, can_read_files=sdk)

    if sdk:
        profile = ProviderProfile(
            name=ProfileName.SDK, provider=ProviderType.SDK, auth_type=AuthType.SESSION
        )
    else:
        profile = ProviderProfile(name="openai", provider="openai", api_key_env="OPENAI_API_KEY")

    with (
        patch(f"{_P}.get_profile", return_value=profile),
        patch(f"{_P}.get_provider", return_value=provider),
        patch(f"{_P}.ensure_provider_loaded"),
    ):
        await run_review_with_profile(
            _make_template(allowed_tools),
            {"input": str(target), "cwd": str(tmp_path)},
            profile=profile.name,
        )
    return captured["prompt"]


@pytest.mark.asyncio
async def test_tool_capable_review_skips_file_body_injection(tmp_path: Path) -> None:
    prompt = await _run(tmp_path, allowed_tools=["read_file", "grep"], sdk=False)

    assert "## File Contents" not in prompt
    assert "SENTINEL FILE BODY" not in prompt
    # The prompt still names the file, so the model knows what to read.
    assert "design.md" in prompt


@pytest.mark.asyncio
async def test_no_tools_review_injects_file_bodies_unchanged(tmp_path: Path) -> None:
    prompt = await _run(tmp_path, allowed_tools=None, sdk=False)

    assert "## File Contents" in prompt
    assert "SENTINEL FILE BODY" in prompt


@pytest.mark.asyncio
async def test_unmigrated_template_injects_exactly_as_before(tmp_path: Path) -> None:
    """Byte-identical regression guard: Claude vocabulary on a non-SDK provider is inert."""
    claude_names = await _run(tmp_path, allowed_tools=["Read", "Glob", "Grep"], sdk=False)
    no_tools = await _run(tmp_path, allowed_tools=None, sdk=False)

    assert claude_names == no_tools
    assert "SENTINEL FILE BODY" in claude_names


@pytest.mark.asyncio
async def test_sdk_provider_unaffected_by_effective_tools_change(tmp_path: Path) -> None:
    with_tools = await _run(tmp_path, allowed_tools=["read_file"], sdk=True)
    without_tools = await _run(tmp_path, allowed_tools=None, sdk=True)

    assert "SENTINEL FILE BODY" not in with_tools
    assert "SENTINEL FILE BODY" not in without_tools
    assert with_tools == without_tools


# ---------------------------------------------------------------------------
# Step-vs-template allowed_tools precedence (slice 265, task 16)
# ---------------------------------------------------------------------------


async def _run_capturing_config(
    tmp_path: Path, *, template_tools: list[str] | None, step_tools: list[str] | None
) -> list[str] | None:
    """Return the allowed_tools that reached the built AgentConfig."""
    captured: dict[str, object] = {}
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

    async def _create_agent(config: object) -> MagicMock:
        captured["config"] = config
        return agent

    provider = MagicMock()
    provider.capabilities = ProviderCapabilities(can_read_files=False)
    provider.create_agent = _create_agent

    profile = ProviderProfile(name="openai", provider="openai", api_key_env="OPENAI_API_KEY")
    with (
        patch(f"{_P}.get_profile", return_value=profile),
        patch(f"{_P}.get_provider", return_value=provider),
        patch(f"{_P}.ensure_provider_loaded"),
    ):
        await run_review_with_profile(
            _make_template(template_tools),
            {"input": "unused", "cwd": str(tmp_path)},
            profile=profile.name,
            allowed_tools=step_tools,
        )
    config = captured["config"]
    return config.allowed_tools  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.asyncio
async def test_step_allowed_tools_overrides_template_allowed_tools(tmp_path: Path) -> None:
    resolved = await _run_capturing_config(
        tmp_path, template_tools=["read_file"], step_tools=["grep", "list_files"]
    )

    assert resolved == ["grep", "list_files"]


@pytest.mark.asyncio
async def test_template_allowed_tools_used_when_step_declares_nothing(tmp_path: Path) -> None:
    resolved = await _run_capturing_config(
        tmp_path, template_tools=["read_file", "grep"], step_tools=None
    )

    assert resolved == ["read_file", "grep"]


@pytest.mark.asyncio
async def test_step_empty_list_overrides_template_to_no_tools(tmp_path: Path) -> None:
    """An explicit empty list is a declaration, not an absence — it disables the template's."""
    resolved = await _run_capturing_config(tmp_path, template_tools=["read_file"], step_tools=[])

    assert resolved == []


# ---------------------------------------------------------------------------
# The diff survives the tools path (issue #81)
#
# Slice 265's plan specified this outcome — "a tool-enabled review's prompt omits
# injected file bodies but retains the diff" — but no test asserted it, and the
# behavior shipped inverted: the git-diff injection lived inside
# _inject_file_contents, which the tools path skips entirely. A live review of a
# 48-file change then spent all 20 loop iterations opening files individually and
# reported that it could not verify the source at all.
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_with_change(tmp_path: Path) -> Path:
    """A git repo with one committed change, for exercising the diff path.

    Sync by design: the subprocess calls are blocking, and the project's ASYNC rules
    forbid running them inside an async function.
    """
    import subprocess

    def _git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True)

    _git("init", "-q")
    _git("config", "user.email", "t@example.com")
    _git("config", "user.name", "t")
    target = tmp_path / "mod.py"
    target.write_text("original = 1\n")
    _git("add", "-A")
    _git("commit", "-qm", "base")
    target.write_text("original = 1\nSENTINEL_ADDED_LINE = 2\n")
    _git("add", "-A")
    _git("commit", "-qm", "change")
    return target


async def _run_with_diff(target: Path, *, allowed_tools: list[str] | None) -> str:
    """Run a review whose inputs carry a diff ref, returning the prompt sent."""
    tmp_path = target.parent
    captured: dict[str, str] = {}
    provider = _capture_provider(captured, can_read_files=False)
    profile = ProviderProfile(name="openai", provider="openai", api_key_env="OPENAI_API_KEY")

    with (
        patch(f"{_P}.get_profile", return_value=profile),
        patch(f"{_P}.get_provider", return_value=provider),
        patch(f"{_P}.ensure_provider_loaded"),
    ):
        await run_review_with_profile(
            _make_template(allowed_tools),
            {"input": str(target), "cwd": str(tmp_path), "diff": "HEAD~1"},
            profile=profile.name,
        )
    return captured["prompt"]


@pytest.mark.asyncio
async def test_tool_enabled_review_retains_the_diff(repo_with_change: Path) -> None:
    """The criterion slice 265 stated: bodies omitted, diff retained."""
    prompt = await _run_with_diff(repo_with_change, allowed_tools=["read_file", "list_files", "grep"])

    # The diff is present — no read-only tool can reconstruct one.
    assert "Git Diff" in prompt
    assert "SENTINEL_ADDED_LINE" in prompt
    # ...while full file bodies are not injected; the model reads those on demand.
    # (The "## File Contents" header is shared by both, so assert on body content:
    # the unchanged first line appears only in a full body, never in the diff's
    # added-line context.)
    assert "### input: mod.py" not in prompt
    assert "original = 1\nSENTINEL_ADDED_LINE" not in prompt


@pytest.mark.asyncio
async def test_no_tools_review_still_gets_diff_and_bodies(repo_with_change: Path) -> None:
    """The no-tools path is unchanged."""
    prompt = await _run_with_diff(repo_with_change, allowed_tools=None)

    assert "Git Diff" in prompt
    assert "SENTINEL_ADDED_LINE" in prompt
