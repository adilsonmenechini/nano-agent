import pytest
import tempfile
import os
from nanoagent.agent import Agent

@pytest.fixture
def agent():
    # Create a temporary directory for the memory database
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    # Create an agent with the temporary db_path
    agent = Agent(db_path=db_path)
    yield agent
    # Cleanup: close the memory connection and remove the temporary directory
    agent.memory.close()
    # Remove the temporary directory
    import shutil
    shutil.rmtree(tmpdir)

def test_agent_initialization(agent):
    assert agent.tools == {}
    assert agent.skills == {}
    assert agent.project_path is None

def test_register_tool(agent):
    class MockTool:
        def __init__(self):
            self.description = "A mock tool"
        def execute(self, **kw):
            return f"result: {kw}"
    t = MockTool()
    agent.register_tool("mock", t)
    assert "mock" in agent.tools
    result = agent.execute_tool("mock", {"x": 1})
    assert result == "result: {'x': 1}"

def test_register_skill(agent):
    # We don't have a skill implementation yet, so we'll use a mock
    class MockSkill:
        def __init__(self):
            self.name = "mock_skill"
            self.description = "A mock skill"
        def execute(self, **kwargs):
            return "mock result"
    skill = MockSkill()
    agent.register_skill("mock_skill", skill)
    assert "mock_skill" in agent.skills
    assert agent.skills["mock_skill"] == skill

def test_remember_and_recall(agent):
    # Remember a value
    agent.remember("test_key", "test_value")
    # Recall the value
    result = agent.recall("test_key")
    assert result == "test_value"

def test_remember_and_recall_with_target_and_scope(agent):
    # Remember a value with specific target and scope
    agent.remember("user_key", "user_value", target="user", scope="global")
    # Recall the value
    result = agent.recall("user_key", target="user", scope="global")
    assert result == "user_value"

def test_run(agent):
    response, messages = agent.run("Hello, agent!")
    assert response == "Agent received: Hello, agent!"

def test_run_with_messages(agent):
    response, messages = agent.run("first", messages=None)
    assert response == "Agent received: first"
    assert messages == []
    response2, messages = agent.run("second", messages=messages)
    assert response2 == "Agent received: second"
    assert messages == []

def test_agent_callbacks(agent):
    import unittest.mock
    from nanoagent.llm.base import LLMResponse, ToolCall

    mock_llm = unittest.mock.MagicMock()
    agent.llm_provider = mock_llm

    # Register a tool
    class MockTool:
        def __init__(self):
            self.description = "A mock tool"
        def execute(self, **kw):
            return "tool result"
    agent.register_tool("mock_tool", MockTool())

    # Set up mock responses: first returns a tool call, second returns final content
    call_1 = ToolCall(id="tc-1", name="mock_tool", arguments={"arg": "val"})
    response_1 = LLMResponse(tool_calls=[call_1])
    response_2 = LLMResponse(content="Final agent response")
    
    mock_llm.chat.side_effect = [response_1, response_2]

    # Callback tracking
    thinking_calls = 0
    tool_calls = []
    tool_results = []

    def on_thinking():
        nonlocal thinking_calls
        thinking_calls += 1

    def on_tool_call(name, args):
        tool_calls.append((name, args))

    def on_tool_result(name, result):
        tool_results.append((name, result))

    agent.on_thinking = on_thinking
    agent.on_tool_call = on_tool_call
    agent.on_tool_result = on_tool_result

    response, messages = agent.run("Hello")

    assert response == "Final agent response"
    assert thinking_calls == 2
    assert tool_calls == [("mock_tool", {"arg": "val"})]
    assert tool_results == [("mock_tool", "tool result")]

    # Assert that tool call arguments are properly double-quoted valid JSON strings
    assistant_tool_msgs = [m for m in messages if m.get("role") == "assistant" and "tool_calls" in m]
    assert len(assistant_tool_msgs) == 1
    tool_msg = assistant_tool_msgs[0]
    assert tool_msg["content"] == ""
    assert tool_msg["tool_calls"][0]["function"]["arguments"] == '{"arg": "val"}'


def test_skill_callbacks(agent):
    class MockSkill:
        def __init__(self):
            self.name = "mock_skill"
            self.description = "A mock skill"
        def execute(self, **kwargs):
            return f"skill result: {kwargs.get('x')}"

    agent.register_skill("mock_skill", MockSkill())

    skill_calls = []
    skill_results = []

    def on_skill_call(name, kwargs):
        skill_calls.append((name, kwargs))

    def on_skill_result(name, result):
        skill_results.append((name, result))

    agent.on_skill_call = on_skill_call
    agent.on_skill_result = on_skill_result

    res = agent.execute_skill("mock_skill", x=42)
    assert res == "skill result: 42"
    assert skill_calls == [("mock_skill", {"x": 42})]
    assert skill_results == [("mock_skill", "skill result: 42")]