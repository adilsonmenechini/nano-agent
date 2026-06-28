import pytest
from nanoagent.llm.base import StreamEvent, LLMResponse


def test_stream_event_dataclass():
    e = StreamEvent(type="content", delta="Hello")
    assert e.type == "content"
    assert e.delta == "Hello"


def test_stream_event_tool_call():
    e = StreamEvent(type="tool_call", delta={"id": "tc-1", "name": "test_tool"})
    assert e.type == "tool_call"
    assert e.delta["id"] == "tc-1"


def test_stream_event_done():
    e = StreamEvent(type="done")
    assert e.type == "done"


def test_base_provider_stream_fallback_uses_non_streaming():
    from nanoagent.llm.base import BaseLLMProvider
    class FakeProvider(BaseLLMProvider):
        def _chat(self, messages, tools=None, system_prompt=None, **kwargs):
            return LLMResponse(content="Hello from fallback")
    p = FakeProvider(api_key="test", base_url="http://test", model="test")
    events = list(p._chat_stream(messages=[{"role": "user", "content": "Hi"}]))
    assert len(events) >= 2
    assert events[-1].type == "done"
    assert events[0].type == "content"


def _make_stream_side_effect(final="Hello from stream"):
    def side_effect(*args, **kwargs):
        if kwargs.get("stream"):
            yield StreamEvent(type="content", delta=final)
            yield StreamEvent(type="done")
        else:
            return LLMResponse(content=final)
    return side_effect


def test_agent_run_stream_yields_events():
    import unittest.mock
    from nanoagent.agent import Agent
    agent = Agent(db_path=":memory:")
    mock_llm = unittest.mock.MagicMock()
    mock_llm.chat.side_effect = _make_stream_side_effect()
    agent.llm_provider = mock_llm
    events = list(agent.run_stream("Test stream"))
    contents = [e for e in events if e.type == "content"]
    assert len(contents) >= 1
    assert any("Hello from stream" in str(c.delta) for c in contents)
    assert events[-1].type == "done"
    agent.memory.close()


def test_agent_run_stream_with_tool_calls():
    import unittest.mock
    from nanoagent.agent import Agent
    agent = Agent(db_path=":memory:")
    mock_llm = unittest.mock.MagicMock()
    class MockTool:
        description = "A mock tool"
        def execute(self, **kw):
            return "tool result"
    agent.register_tool("mock_tool", MockTool())
    agent.llm_provider = mock_llm
    def side_effect(*args, **kwargs):
        if kwargs.get("stream"):
            yield StreamEvent(type="tool_call", delta={
                "id": "tc-1", "name": "mock_tool", "arguments": {"arg": "val"},
            })
            yield StreamEvent(type="done")
        else:
            return LLMResponse(content="Final response")
    mock_llm.chat.side_effect = side_effect
    events = list(agent.run_stream("Test with tools"))
    assert events[-1].type == "done"
    agent.memory.close()


def test_agent_run_stream_cancellation_during_execution():
    import unittest.mock
    from nanoagent.agent import Agent
    agent = Agent(db_path=":memory:")
    mock_llm = unittest.mock.MagicMock()
    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if kwargs.get("stream"):
            yield StreamEvent(type="content", delta=f"chunk-{call_count}")
            yield StreamEvent(type="done")
        else:
            return LLMResponse(content="done")
    mock_llm.chat.side_effect = side_effect
    agent.llm_provider = mock_llm
    gen = agent.run_stream("Test cancel")
    first = next(gen)
    assert first.type == "content"
    assert "chunk" in str(first.delta)
    agent.cancelled = True
    done = next(gen)
    assert done.type == "done"
    agent.memory.close()


def test_agent_run_stream_no_provider():
    from nanoagent.agent import Agent
    agent = Agent(db_path=":memory:")
    events = list(agent.run_stream("No provider"))
    contents = [e for e in events if e.type == "content"]
    assert any("Agent received" in str(c.delta) for c in contents)
    assert events[-1].type == "done"
    agent.memory.close()
