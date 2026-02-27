"""Tests for providers/openai/translation.py."""

from __future__ import annotations

from orchestration.core.models import MessageType
from orchestration.providers.openai.translation import (
    build_messages,
    build_text_message,
    build_tool_call_message,
)

_AGENT = "test-agent"
_MODEL = "gpt-4o-mini"


class TestBuildTextMessage:
    def test_non_empty_returns_chat_message(self) -> None:
        msg = build_text_message("Hello", _AGENT, _MODEL)
        assert msg is not None
        assert msg.content == "Hello"
        assert msg.sender == _AGENT
        assert msg.recipients == ["all"]
        assert msg.message_type == MessageType.chat
        assert msg.metadata["provider"] == "openai"
        assert msg.metadata["model"] == _MODEL

    def test_empty_string_returns_none(self) -> None:
        assert build_text_message("", _AGENT, _MODEL) is None

    def test_whitespace_only_returns_none(self) -> None:
        assert build_text_message("   ", _AGENT, _MODEL) is None


class TestBuildToolCallMessage:
    def test_metadata_fields_present(self) -> None:
        tc = {
            "id": "call_abc",
            "function": {"name": "my_tool", "arguments": '{"x": 1}'},
        }
        msg = build_tool_call_message(tc, _AGENT)
        assert msg.message_type == MessageType.system
        assert msg.metadata["provider"] == "openai"
        assert msg.metadata["type"] == "tool_call"
        assert msg.metadata["tool_call_id"] == "call_abc"
        assert msg.metadata["tool_name"] == "my_tool"
        assert msg.metadata["tool_arguments"] == '{"x": 1}'

    def test_content_contains_tool_name(self) -> None:
        tc = {"id": "c1", "function": {"name": "search", "arguments": "{}"}}
        msg = build_tool_call_message(tc, _AGENT)
        assert "search" in msg.content


class TestBuildMessages:
    def test_text_only(self) -> None:
        msgs = build_messages("Hello", [], _AGENT, _MODEL)
        assert len(msgs) == 1
        assert msgs[0].message_type == MessageType.chat

    def test_tool_calls_only(self) -> None:
        tcs = [
            {"id": "c1", "function": {"name": "tool_a", "arguments": "{}"}},
            {"id": "c2", "function": {"name": "tool_b", "arguments": "{}"}},
        ]
        msgs = build_messages("", tcs, _AGENT, _MODEL)
        assert len(msgs) == 2
        assert all(m.message_type == MessageType.system for m in msgs)

    def test_mixed_text_and_tool_call(self) -> None:
        tcs = [{"id": "c1", "function": {"name": "tool_a", "arguments": "{}"}}]
        msgs = build_messages("Some text", tcs, _AGENT, _MODEL)
        assert len(msgs) == 2
        assert msgs[0].message_type == MessageType.chat
        assert msgs[1].message_type == MessageType.system

    def test_empty_returns_empty_list(self) -> None:
        assert build_messages("", [], _AGENT, _MODEL) == []
