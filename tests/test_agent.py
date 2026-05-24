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