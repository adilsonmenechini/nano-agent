"""Additional lmstudio.py branch coverage for stream and tool-call parsing."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import openai

from nanoagent.llm.lmstudio import LMStudioProvider


class TestLMStudioProviderStream:
    def test_stream_text_delta(self):
        p = LMStudioProvider("key", "url", "model")
        p.client = MagicMock()
        c1 = MagicMock(
            choices=[MagicMock(delta=MagicMock(content="h", tool_calls=None))],
            usage=MagicMock(prompt_tokens=0, completion_tokens=0),
        )
        c2 = MagicMock(
            choices=[MagicMock(delta=MagicMock(content="i", tool_calls=None))],
            usage=MagicMock(prompt_tokens=0, completion_tokens=0),
        )
        p.client.chat.completions.create.return_value = iter([c1, c2])
        events = list(p._chat_stream([{"role": "user", "content": "hi"}]))
        texts = [e.delta for e in events if e.type == "content"]
        assert texts == ["h", "i"]

    def test_stream_no_choices_yields_only_done(self):
        p = LMStudioProvider("key", "url", "model")
        p.client = MagicMock()
        no_choices = MagicMock(choices=[])
        p.client.chat.completions.create.return_value = iter([no_choices])
        events = list(p._chat_stream([{"role": "user", "content": "hi"}]))
        assert [e.type for e in events] == ["done"]

    def test_stream_usage_none(self):
        # usage is None; LMStudioProvider gracefully handles f-string style `usage`.
        p = LMStudioProvider("key", "url", "model")
        p.client = MagicMock()
        p.client.chat.completions.create.return_value = iter([
            MagicMock(choices=[], usage=None),
        ])
        events = list(p._chat_stream([{"role": "user", "content": "hi"}]))
        assert events  # at least "done"

    def test_stream_with_system_prompt(self):
        p = LMStudioProvider("key", "url", "model")
        p.client = MagicMock()
        p.client.chat.completions.create.return_value = iter([
            MagicMock(choices=[MagicMock(delta=MagicMock(content="ok"))], usage=MagicMock(prompt_tokens=0, completion_tokens=0)),
        ])
        events = list(p._chat_stream([{"role": "user", "content": "hi"}], system_prompt="sys"))
        assert any(e.delta == "ok" for e in events)
        passed_messages = p.client.chat.completions.create.call_args.kwargs["messages"]
        assert {"role": "system", "content": "sys"} in passed_messages

    def test_chat_stream_generator(self):
        p = LMStudioProvider("key", "url", "model")
        p.client = MagicMock()
        p.client.chat.completions.create.return_value = iter([
            MagicMock(choices=[], usage=MagicMock(prompt_tokens=0, completion_tokens=0)),
        ])
        result = p.chat([{"role": "user", "content": "hi"}], stream=True)
        events = list(result)
        assert events
        assert events[-1].type == "done"


class TestLMStudioToolCallParsing:
    def _make_tc(self, id_, name_, arguments):
        fn = MagicMock()
        fn.name = name_
        fn.arguments = arguments
        tc = MagicMock()
        tc.id = id_
        tc.type = "function"
        tc.function = fn
        return tc

    def test_multiple_tool_calls(self):
        p = LMStudioProvider("key", "url", "model")
        p.client = MagicMock()
        tc1 = self._make_tc("c1", "search", '{"q":"x"}')
        tc2 = self._make_tc("c2", "calc", '{"n":5}')
        mc = MagicMock(
            choices=[MagicMock(message=MagicMock(content=None, tool_calls=[tc1, tc2]))],
            usage=MagicMock(prompt_tokens=2, completion_tokens=3),
        )
        p.client.chat.completions.create.return_value = mc
        resp = p.chat([{"role": "user", "content": "hi"}], tools=[])
        assert len(resp.tool_calls) == 2
        assert resp.tool_calls[0].id == "c1"
        assert resp.tool_calls[1].id == "c2"

    def test_tool_calls_arguments_parsed(self):
        p = LMStudioProvider("key", "url", "model")
        p.client = MagicMock()
        tc = self._make_tc("c1", "tool_fn", '{"key": 42}')
        mc = MagicMock(
            choices=[MagicMock(message=MagicMock(content=None, tool_calls=[tc]))],
            usage=MagicMock(prompt_tokens=1, completion_tokens=1),
        )
        p.client.chat.completions.create.return_value = mc
        resp = p.chat([{"role": "user", "content": "hi"}], tools=[])
        assert resp.tool_calls[0].arguments == {"key": 42}
