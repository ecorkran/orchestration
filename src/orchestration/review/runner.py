"""Review execution: build prompt, run ClaudeSDKClient session, parse result."""

from __future__ import annotations

import logging
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ClaudeSDKError,
    TextBlock,
)

from orchestration.review.models import ReviewResult
from orchestration.review.parsers import parse_review_output
from orchestration.review.templates import ReviewTemplate

_logger = logging.getLogger(__name__)

MAX_PARSE_RETRIES = 10


def _extract_text(message: Any) -> str:
    """Extract text content from an SDK message.

    Only extracts from AssistantMessage — ResultMessage duplicates the
    assistant content and is skipped to avoid doubled output.
    """
    if isinstance(message, AssistantMessage):
        parts: list[str] = []
        for block in message.content:
            if isinstance(block, TextBlock):
                parts.append(block.text)
        return "\n".join(parts)
    return ""


async def run_review(
    template: ReviewTemplate,
    inputs: dict[str, str],
    *,
    rules_content: str | None = None,
    model: str | None = None,
) -> ReviewResult:
    """Execute a review and return structured results.

    This is the primary interface for both CLI and programmatic consumers.
    Creates an ephemeral ClaudeSDKClient session per review.

    If rules_content is provided, it is appended to the template's system
    prompt as additional review rules.

    Model resolution: explicit model kwarg overrides template.model.
    Pass None to use the SDK default.
    """
    prompt = template.build_prompt(inputs)

    system_prompt = template.system_prompt
    if rules_content:
        system_prompt += f"\n\n## Additional Review Rules\n\n{rules_content}"

    resolved_model = model if model is not None else template.model

    options_kwargs: dict[str, object] = {
        "system_prompt": system_prompt,
        "allowed_tools": template.allowed_tools,
        "permission_mode": template.permission_mode,
        "setting_sources": template.setting_sources,
        "cwd": inputs.get("cwd"),
        "hooks": template.hooks,
    }
    if resolved_model is not None:
        options_kwargs["model"] = resolved_model

    options = ClaudeAgentOptions(**options_kwargs)  # type: ignore[arg-type]

    raw_output = ""
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        retries = 0
        while True:
            try:
                async for message in client.receive_response():
                    raw_output += _extract_text(message)
                break  # normal completion (ResultMessage received)
            except ClaudeSDKError as exc:
                # The SDK's MessageParseError (not publicly exported) is
                # raised when the CLI emits message types the parser doesn't
                # recognize. rate_limit_event is benign — the CLI handles
                # backoff internally. We restart receive_response() on the
                # same session; the underlying anyio channel is still intact.
                if "rate_limit_event" in str(exc) and retries < MAX_PARSE_RETRIES:
                    retries += 1
                    _logger.debug(
                        "Rate limit event %d/%d (CLI handles backoff internally)",
                        retries,
                        MAX_PARSE_RETRIES,
                    )
                    continue  # restart receive_response() on same session
                raise

    return parse_review_output(
        raw_output=raw_output,
        template_name=template.name,
        input_files=inputs,
        model=resolved_model,
    )
