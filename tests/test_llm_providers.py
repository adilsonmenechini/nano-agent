"""Tests for LLM provider error paths and edge branches."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import anthropic
import pytest

from nanoagent.llm.base import BaseLLMProvider, LLMResponse, StreamEvent, ToolCall


class FakeProvider(BaseLLMProvider):
    def _chat(self, messages, tools=None, system_prompt=None, **kwargs):
        return LLMResponse(content="ok", usage={"prompt_tokens": 5, "completion_tokens": 3})


class TestBaseLLMProvider:
    def test_generate(self):
        p = FakeProvider("key", "url", "model")
        with patch.object(p, "_chat", return_value=LLMResponse(content="hi")):
            assert p.generate("hi") == "hi"

    def test_generate_empty_content(self):
        p = FakeProvider("key", "url", "model")
        with patch.object(p, "_chat", return_value=LLMResponse(content=None)):
            assert p.generate("hi") == ""

    def test_generate_with_tools_returns_content(self):
        p = FakeProvider("key", "url", "model")
        with patch.object(p, "_chat", return_value=LLMResponse(content="done")):
            assert p.generate_with_tools("prompt", [{"type": "function"}]) == "done"

    def test_generate_with_tools_returns_tool_calls(self):
        p = FakeProvider("key", "url", "model")
        resp = LLMResponse(
            tool_calls=[ToolCall(id="c1", name="search", arguments={"q": "test"})]
        )
        with patch.object(p, "_chat", return_value=resp):
            import json as _json
            result = p.generate_with_tools("prompt", [{"type": "function"}])
            parsed = _json.loads(result)
            assert parsed[0]["id"] == "c1"

    def test_chat_false_stream(self):
        p = FakeProvider("key", "url", "model")
        with patch.object(p, "_chat", return_value=LLMResponse(content="resp")) as m:
            p.chat([{"role": "user", "content": "hi"}], stream=False)
            assert m.called

    def test_chat_true_stream(self):
        p = FakeProvider("key", "url", "model")
        events = [StreamEvent(type="content", delta="h"), StreamEvent(type="done")]
        with patch.object(p, "_chat_stream", return_value=iter(events)) as m:
            result = list(p.chat([{"role": "user", "content": "hi"}], stream=True))
            assert result == events
            assert m.called


class TestAnthropicProvider:
    def test_chat_success(self):
        from nanoagent.llm.anthropic import AnthropicProvider
        block = MagicMock()
        block.type = "text"
        block.text = "hi"
        mock_resp = MagicMock()
        mock_resp.content = [block]
        mock_resp.stop_reason = "end_turn"
        mock_resp.usage = MagicMock(input_tokens=1, output_tokens=2)
        with patch("anthropic.Anthropic") as MockAnthropic:
            client = MagicMock()
            client.messages.create.return_value = mock_resp
            MockAnthropic.return_value = client
            p = AnthropicProvider("key", "url", "model")
            result = p.chat([{"role": "user", "content": "hi"}])
            assert result.content == "hi"
            assert result.usage["input_tokens"] == 1

    def test_chat_with_tool_use(self):
        from nanoagent.llm.anthropic import AnthropicProvider
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "response"
        tc = MagicMock()
        tc.type = "tool_use"
        tc.id = "tool_1"
        tc.name = "search"
        tc.input = {"q": "test"}
        mock_resp = MagicMock()
        mock_resp.content = [text_block, tc]
        mock_resp.stop_reason = "tool_use"
        mock_resp.usage = MagicMock(input_tokens=5, output_tokens=10)
        with patch("anthropic.Anthropic") as MockAnthropic:
            client = MagicMock()
            client.messages.create.return_value = mock_resp
            MockAnthropic.return_value = client
            p = AnthropicProvider("key", "url", "model")
            result = p.chat([{"role": "user", "content": "hi"}], tools=[])
            assert result.tool_calls is not None
            assert result.tool_calls[0].name == "search"

    def test_chat_api_error(self):
        from nanoagent.llm.anthropic import AnthropicProvider
        with patch("anthropic.Anthropic") as MockAnthropic:
            client = MagicMock()
            client.messages.create.side_effect = RuntimeError("upstream failure")
            MockAnthropic.return_value = client
            p = AnthropicProvider("key", "url", "model")
            with pytest.raises(RuntimeError, match="Anthropic API error"):
                p.chat([{"role": "user", "content": "hi"}])

    def test_chat_api_error_fallback(self):
        from nanoagent.llm.anthropic import AnthropicProvider
        with patch("anthropic.Anthropic") as MockAnthropic:
            client = MagicMock()
            client.messages.create.side_effect = anthropic.BadRequestError(
                message="some issue",
                response=MagicMock(),
                body={"error": {"message": "some issue"}},
            )
            MockAnthropic.return_value = client
            p = AnthropicProvider("key", "url", "model")
            # anthropic.py wraps ALL exceptions into RuntimeError("Anthropic API error: ...")
            with pytest.raises(RuntimeError, match="Anthropic API error"):
                p.chat([{"role": "user", "content": "hi"}])


class TestLMStudioProvider:
    def test_chat_success(self):
        from nanoagent.llm.lmstudio import LMStudioProvider
        lp = LMStudioProvider("key", "url", "model")
        mc = MagicMock()
        choice = MagicMock()
        choice.message.content = "hello"
        choice.message.tool_calls = None
        mc.choices = [choice]
        mc.usage = MagicMock(prompt_tokens=2, completion_tokens=3)
        lp.client = MagicMock()
        lp.client.chat.completions.create.return_value = mc
        result = lp.chat([{"role": "user", "content": "hi"}])
        assert result.content == "hello"

    def test_chat_bad_request_jinja(self):
        from nanoagent.llm.lmstudio import LMStudioProvider
        import openai
        lp = LMStudioProvider("key", "url", "model")
        err = openai.BadRequestError(
            message="jinja prompt template error",
            response=MagicMock(),
            body={"error": {"message": "jinja prompt template error"}},
        )
        lp.client = MagicMock()
        lp.client.chat.completions.create.side_effect = err
        with pytest.raises(RuntimeError, match="broken prompt template"):
            lp.chat([{"role": "user", "content": "hi"}])

    def test_chat_bad_request_other(self):
        from nanoagent.llm.lmstudio import LMStudioProvider
        import openai
        lp = LMStudioProvider("key", "url", "model")
        err = openai.BadRequestError(
            message="other error",
            response=MagicMock(),
            body={"error": {"message": "other error"}},
        )
        lp.client = MagicMock()
        lp.client.chat.completions.create.side_effect = err
        with pytest.raises(RuntimeError, match="LM Studio API error"):
            lp.chat([{"role": "user", "content": "hi"}])
