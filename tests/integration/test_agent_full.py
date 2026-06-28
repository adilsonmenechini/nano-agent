import pytest


def test_full_agent_flow_mocked():
    import unittest.mock
    from nanoagent.agent import Agent
    from nanoagent.llm.base import LLMResponse, ToolCall, StreamEvent

    agent = Agent(db_path=":memory:")
    mock_llm = unittest.mock.MagicMock()

    class MockTool:
        description = "A mock tool"
        def execute(self, **kw):
            return "tool executed"

    agent.register_tool("mock_tool", MockTool())

    tool_call_1 = ToolCall(id="t1", name="mock_tool", arguments={"arg": "val"})
    response_1 = LLMResponse(tool_calls=[tool_call_1])
    response_2 = LLMResponse(content="Final answer from agent")

    mock_llm.chat.side_effect = [response_1, response_2]
    agent.llm_provider = mock_llm

    response, messages = agent.run("Do something")
    assert "Final answer" in response
    assert len(messages) >= 3

    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    assert "tool executed" in tool_msgs[0]["content"]
    agent.memory.close()


def test_full_agent_stream_flow_mocked():
    import unittest.mock
    from nanoagent.agent import Agent
    from nanoagent.llm.base import StreamEvent, ToolCall, LLMResponse

    agent = Agent(db_path=":memory:")
    mock_llm = unittest.mock.MagicMock()

    class MockTool:
        description = "A mock tool"
        def execute(self, **kw):
            return "stream tool executed"

    agent.register_tool("mock_tool", MockTool())

    def side_effect(*args, **kwargs):
        if kwargs.get("stream"):
            yield StreamEvent(type="tool_call", delta={
                "id": "t1", "name": "mock_tool", "arguments": {"arg": "val"},
            })
            yield StreamEvent(type="done")
        else:
            return LLMResponse(content="Final stream answer")

    mock_llm.chat.side_effect = side_effect
    agent.llm_provider = mock_llm

    events = list(agent.run_stream("Do stream thing"))
    assert events[-1].type == "done"
    agent.memory.close()
