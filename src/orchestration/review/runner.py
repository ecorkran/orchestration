"""Review execution: build prompt, run ClaudeSDKClient session, parse result."""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from orchestration.review.models import ReviewResult
from orchestration.review.parsers import parse_review_output
from orchestration.review.templates import ReviewTemplate


def _extract_text(message: Any) -> str:
    """Extract text content from an SDK message."""
    if isinstance(message, AssistantMessage):
        parts: list[str] = []
        for block in message.content:
            if isinstance(block, TextBlock):
                parts.append(block.text)
        return "\n".join(parts)
    if isinstance(message, ResultMessage):
        return str(message.result) if message.result else ""
    return ""


async def run_review(
    template: ReviewTemplate,
    inputs: dict[str, str],
) -> ReviewResult:
    """Execute a review and return structured results.

    This is the primary interface for both CLI and programmatic consumers.
    Creates an ephemeral ClaudeSDKClient session per review.
    """
    prompt = template.build_prompt(inputs)

    options = ClaudeAgentOptions(
        system_prompt=template.system_prompt,
        allowed_tools=template.allowed_tools,
        permission_mode=template.permission_mode,
        setting_sources=template.setting_sources,
        cwd=inputs.get("cwd"),
        hooks=template.hooks,
    )

    raw_output = ""
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            raw_output += _extract_text(message)

    return parse_review_output(
        raw_output=raw_output,
        template_name=template.name,
        input_files=inputs,
    )
