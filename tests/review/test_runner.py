"""Tests for review runner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_agent_sdk import ClaudeSDKError

from orchestration.review.models import Verdict
from orchestration.review.runner import run_review
from orchestration.review.templates import InputDef, ReviewTemplate


@pytest.fixture
def arch_template() -> ReviewTemplate:
    return ReviewTemplate(
        name="arch",
        description="Arch review",
        system_prompt="You are an architectural reviewer.",
        allowed_tools=["Read", "Glob", "Grep"],
        permission_mode="bypassPermissions",
        setting_sources=None,
        required_inputs=[
            InputDef(name="input", description="Doc to review"),
            InputDef(name="against", description="Arch doc"),
        ],
        optional_inputs=[
            InputDef(name="cwd", description="Working dir", default="."),
        ],
        prompt_template="Review {input} against {against}",
    )


MOCK_REVIEW_OUTPUT = """\
## Summary
CONCERNS

## Findings

### [CONCERN] Missing validation
Input is not validated.

### [PASS] Good structure
Clean module layout.
"""


def _make_mock_client() -> MagicMock:
    """Create a mock ClaudeSDKClient."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.query = AsyncMock()

    # Messages yielded by receive_response (content doesn't matter when
    # _extract_text is patched)
    sentinel = MagicMock()

    async def _receive():  # type: ignore[no-untyped-def]
        yield sentinel

    client.receive_response = _receive
    return client


class TestRunReview:
    """Test run_review orchestration logic."""

    @pytest.mark.asyncio
    async def test_options_constructed_from_template(
        self, arch_template: ReviewTemplate
    ) -> None:
        mock_client = _make_mock_client()

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ) as mock_cls,
            patch(
                "orchestration.review.runner._extract_text",
                return_value="",
            ),
        ):
            inputs = {"input": "s.md", "against": "a.md", "cwd": "/proj"}
            await run_review(arch_template, inputs)

            options = mock_cls.call_args.kwargs["options"]
            assert options.system_prompt == "You are an architectural reviewer."
            assert options.allowed_tools == ["Read", "Glob", "Grep"]
            assert options.permission_mode == "bypassPermissions"
            assert options.cwd == "/proj"
            assert options.setting_sources is None

    @pytest.mark.asyncio
    async def test_query_called_with_built_prompt(
        self, arch_template: ReviewTemplate
    ) -> None:
        mock_client = _make_mock_client()

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ),
            patch(
                "orchestration.review.runner._extract_text",
                return_value="",
            ),
        ):
            inputs = {"input": "a.md", "against": "b.md"}
            await run_review(arch_template, inputs)
            mock_client.query.assert_awaited_once_with("Review a.md against b.md")

    @pytest.mark.asyncio
    async def test_returns_review_result_with_parsed_output(
        self, arch_template: ReviewTemplate
    ) -> None:
        mock_client = _make_mock_client()

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ),
            patch(
                "orchestration.review.runner._extract_text",
                return_value=MOCK_REVIEW_OUTPUT,
            ),
        ):
            inputs = {"input": "a.md", "against": "b.md"}
            result = await run_review(arch_template, inputs)
            assert result.verdict == Verdict.CONCERNS
            assert len(result.findings) == 2
            assert result.template_name == "arch"
            assert result.input_files == inputs
            assert result.findings[0].title == "Missing validation"

    @pytest.mark.asyncio
    async def test_explicit_model_passed_to_options(
        self, arch_template: ReviewTemplate
    ) -> None:
        mock_client = _make_mock_client()

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ) as mock_cls,
            patch(
                "orchestration.review.runner._extract_text",
                return_value="",
            ),
        ):
            inputs = {"input": "s.md", "against": "a.md"}
            await run_review(arch_template, inputs, model="opus")

            options = mock_cls.call_args.kwargs["options"]
            assert options.model == "opus"

    @pytest.mark.asyncio
    async def test_template_model_used_as_fallback(self) -> None:
        template = ReviewTemplate(
            name="modeled",
            description="Template with model",
            system_prompt="Review.",
            allowed_tools=["Read"],
            permission_mode="bypassPermissions",
            setting_sources=None,
            required_inputs=[],
            optional_inputs=[],
            model="sonnet",
            prompt_template="Review all.",
        )
        mock_client = _make_mock_client()

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ) as mock_cls,
            patch(
                "orchestration.review.runner._extract_text",
                return_value="",
            ),
        ):
            await run_review(template, {})
            options = mock_cls.call_args.kwargs["options"]
            assert options.model == "sonnet"

    @pytest.mark.asyncio
    async def test_explicit_model_overrides_template(self) -> None:
        template = ReviewTemplate(
            name="modeled",
            description="Template with model",
            system_prompt="Review.",
            allowed_tools=["Read"],
            permission_mode="bypassPermissions",
            setting_sources=None,
            required_inputs=[],
            optional_inputs=[],
            model="sonnet",
            prompt_template="Review all.",
        )
        mock_client = _make_mock_client()

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ) as mock_cls,
            patch(
                "orchestration.review.runner._extract_text",
                return_value="",
            ),
        ):
            await run_review(template, {}, model="opus")
            options = mock_cls.call_args.kwargs["options"]
            assert options.model == "opus"

    @pytest.mark.asyncio
    async def test_model_stored_in_result(self, arch_template: ReviewTemplate) -> None:
        mock_client = _make_mock_client()

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ),
            patch(
                "orchestration.review.runner._extract_text",
                return_value=MOCK_REVIEW_OUTPUT,
            ),
        ):
            inputs = {"input": "a.md", "against": "b.md"}
            result = await run_review(arch_template, inputs, model="opus")
            assert result.model == "opus"

    @pytest.mark.asyncio
    async def test_no_model_omitted_from_options(
        self, arch_template: ReviewTemplate
    ) -> None:
        """When no model is specified, ClaudeAgentOptions should not receive model."""
        mock_client = _make_mock_client()

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ) as mock_cls,
            patch(
                "orchestration.review.runner._extract_text",
                return_value="",
            ),
        ):
            inputs = {"input": "s.md", "against": "a.md"}
            await run_review(arch_template, inputs)

            options = mock_cls.call_args.kwargs["options"]
            assert options.model is None

    @pytest.mark.asyncio
    async def test_hooks_passed_to_options(self) -> None:
        template = ReviewTemplate(
            name="hooked",
            description="Template with hooks",
            system_prompt="Review.",
            allowed_tools=["Read"],
            permission_mode="bypassPermissions",
            setting_sources=None,
            required_inputs=[],
            optional_inputs=[],
            hooks={"PostToolUse": {"command": "echo done"}},
            prompt_template="Review all.",
        )
        mock_client = _make_mock_client()

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ) as mock_cls,
            patch(
                "orchestration.review.runner._extract_text",
                return_value="## Summary\nPASS\n",
            ),
        ):
            await run_review(template, {})
            options = mock_cls.call_args.kwargs["options"]
            assert options.hooks == {"PostToolUse": {"command": "echo done"}}


class TestRateLimitEventHandling:
    """Test graceful handling of rate_limit_event parse errors."""

    @pytest.mark.asyncio
    async def test_rate_limit_event_recovered(
        self, arch_template: ReviewTemplate
    ) -> None:
        """rate_limit_event causes receive_response restart, review completes."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.query = AsyncMock()

        call_count = 0
        sentinel = MagicMock()

        async def _receive():  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ClaudeSDKError("Unknown message type: rate_limit_event")
            yield sentinel

        mock_client.receive_response = _receive

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ),
            patch(
                "orchestration.review.runner._extract_text",
                return_value=MOCK_REVIEW_OUTPUT,
            ),
        ):
            inputs = {"input": "a.md", "against": "b.md"}
            result = await run_review(arch_template, inputs)
            assert result.verdict == Verdict.CONCERNS
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_parse_retries_exhausted(self, arch_template: ReviewTemplate) -> None:
        """After MAX_PARSE_RETRIES, the error propagates."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.query = AsyncMock()

        async def _always_fail():  # type: ignore[no-untyped-def]
            raise ClaudeSDKError("Unknown message type: rate_limit_event")
            yield  # makes this an async generator  # noqa: RUF027

        mock_client.receive_response = _always_fail

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ),
        ):
            inputs = {"input": "a.md", "against": "b.md"}
            with pytest.raises(ClaudeSDKError, match="rate_limit_event"):
                await run_review(arch_template, inputs)

    @pytest.mark.asyncio
    async def test_non_rate_limit_sdk_error_propagates(
        self, arch_template: ReviewTemplate
    ) -> None:
        """Non-rate-limit ClaudeSDKError is not caught."""
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.query = AsyncMock()

        async def _other_error():  # type: ignore[no-untyped-def]
            raise ClaudeSDKError("Connection lost")
            yield  # makes this an async generator  # noqa: RUF027

        mock_client.receive_response = _other_error

        with (
            patch(
                "orchestration.review.runner.ClaudeSDKClient",
                return_value=mock_client,
            ),
        ):
            inputs = {"input": "a.md", "against": "b.md"}
            with pytest.raises(ClaudeSDKError, match="Connection lost"):
                await run_review(arch_template, inputs)
