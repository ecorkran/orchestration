"""Translation helpers: OpenAI response data → orchestration Message objects."""

from __future__ import annotations

from orchestration.core.models import Message, MessageType


def build_text_message(
    text: str,
    agent_name: str,
    model: str,
) -> Message | None:
    """Return a chat Message for *text*, or ``None`` if text is empty/whitespace."""
    if not text or not text.strip():
        return None
    return Message(
        sender=agent_name,
        recipients=["all"],
        content=text,
        message_type=MessageType.chat,
        metadata={"provider": "openai", "model": model},
    )


def build_tool_call_message(tool_call: dict[str, object], agent_name: str) -> Message:
    """Return a system Message surfacing an OpenAI tool call."""
    function: dict[str, object] = tool_call.get("function", {})  # type: ignore[assignment]
    tool_name = function.get("name", "")
    return Message(
        sender=agent_name,
        recipients=["all"],
        content=f"Tool call: {tool_name}",
        message_type=MessageType.system,
        metadata={
            "provider": "openai",
            "type": "tool_call",
            "tool_call_id": tool_call.get("id", ""),
            "tool_name": tool_name,
            "tool_arguments": function.get("arguments", ""),
        },
    )


def build_messages(
    text_buffer: str,
    tool_calls_list: list[dict[str, object]],
    agent_name: str,
    model: str,
) -> list[Message]:
    """Build the full list of Messages from accumulated text and tool calls.

    Text message comes first (if non-empty), then one system Message per tool call.
    """
    messages: list[Message] = []
    text_msg = build_text_message(text_buffer, agent_name, model)
    if text_msg is not None:
        messages.append(text_msg)
    for tc in tool_calls_list:
        messages.append(build_tool_call_message(tc, agent_name))
    return messages
