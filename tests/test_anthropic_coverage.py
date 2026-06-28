"""Additional anthropic.py branch coverage for stream + tool_use."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import anthropic
import pytest

from nanoagent.llm.base import StreamEvent, ToolCall


def _mk_text_delta_chunk(text):
    delta_mock = MagicMock(type="text_delta", text=text)
    return MagicMock(type="content_block_delta", delta=delta_mock)


def _mk_tool_start_chunk(id_, name_, input_):
    content = MagicMock(type="tool_use")
    content.id = id_
    content.name = name_
    content.input = input_
    return MagicMock(type="content_block_start", content_block=content)


class TestAnthropicStream:
    def test_stream_text_delta(self):
        with patch("anthropic.Anthropic") as MockAnthropic:
            client = MagicMock()
            MockAnthropic.return_value = client
            from nanoagent.llm.anthropic import AnthropicProvider
            p = AnthropicProvider("key", "url", "model")
            p.client = client
            client.messages.create.return_value = iter([
                _mk_text_delta_chunk("h"),
                _mk_text_delta_chunk("i"),
                MagicMock(type="content_block_stop"),
            ])
            events = list(p._chat_stream([{"role": "user", "content": "hi"}]))
            texts = [e.delta for e in events if e.type == "content"]
            assert texts == ["h", "i"]
            assert any(e.type == "done" for e in events)

    def test_stream_tool_call_delta(self):
        with patch("anthropic.Anthropic") as MockAnthropic:
            client = MagicMock()
            MockAnthropic.return_value = client
            from nanoagent.llm.anthropic import AnthropicProvider
            p = AnthropicProvider("key", "url", "model")
            p.client = client
            client.messages.create.return_value = iter([
                _mk_tool_start_chunk("id1", "fn", {"a": 1}),
            ])
            events = list(p._chat_stream([{"role": "user", "content": "hi"}]))
            tcs = [e for e in events if e.type == "tool_call"]
            assert len(tcs) == 1
            assert tcs[0].delta == {"id": "id1", "name": "fn", "input": {"a": 1}}
            assert any(e.type == "done" for e in events)

    def test_stream_non_tool_block_skipped(self):
        # content_block_start with type != "tool_use" yields no events (branch is a no-op).
        with patch("anthropic.Anthropic") as MockAnthropic:
            client = MagicMock()
            MockAnthropic.return_value = client
            from nanoagent.llm.anthropic import AnthropicProvider
            p = AnthropicProvider("key", "url", "model")
            p.client = client
            text_block = MagicMock()
            text_block.type = "text"  # non-tool block
            cb = MagicMock(type="content_block_start", content_block=text_block)
            client.messages.create.return_value = iter([cb])
            events = list(p._chat_stream([{"role": "user", "content": "hi"}]))
            assert [e.type for e in events] == ["done"]


class TestAnthropicToolCallInChat:
    def test_tool_use_populates_tool_calls(self):
        with patch("anthropic.Anthropic") as MockAnthropic:
            client = MagicMock()
            MockAnthropic.return_value = client
            from nanoagent.llm.anthropic import AnthropicProvider
            p = AnthropicProvider("key", "url", "model")
            p.client = client
            text_block = MagicMock(type="text", text="response")
            tc = MagicMock(type="tool_use", id="id1")
            tc.name = "search"
            tc.input = {"q": "test"}
            mock_resp = MagicMock(content=[text_block, tc],
                                  stop_reason="tool_use",
                                  usage=MagicMock(input_tokens=5, output_tokens=10))
            client.messages.create.return_value = mock_resp
            result = p.chat([{"role": "user", "content": "hi"}])
            assert result.content == "response"
            assert result.tool_calls is not None
            assert result.tool_calls[0].id == "id1"
            assert result.tool_calls[0].name == "search"
            assert result.tool_calls[0].arguments == {"q": "test"}
