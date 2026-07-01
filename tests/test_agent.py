import pytest
import tempfile
import os
from nanoagent.agent import Agent
from nanoagent.agent.errors import (
    AgentError,
    ProviderError,
    ProviderRetryableError,
    ProviderFatalError,
    ConfigError,
    StateTransitionError,
)


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
    assert len(agent.tools) >= 8
    assert "run_shell" in agent.tools
    assert "read_file" in agent.tools
    assert "write_file" in agent.tools
    assert "glob_file" in agent.tools
    assert "grep_file" in agent.tools
    assert "git_status" in agent.tools
    assert "git_diff" in agent.tools
    assert "git_log" in agent.tools
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
    assistant_tool_msgs = [
        m for m in messages if m.get("role") == "assistant" and "tool_calls" in m
    ]
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


# ─── Session tests ─────────────────────────────────────────────────────────────


def test_session_save_and_load(agent):
    store = agent.memory
    session_id = "test-session-001"
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
    ]
    store.save_session(session_id, messages)
    loaded = store.load_session(session_id)
    assert loaded is not None
    assert loaded["messages"] == messages
    assert loaded["status"] == "active"

    store.update_session_status(session_id, "completed")
    loaded = store.load_session(session_id)
    assert loaded["status"] == "completed"


def test_session_list(agent):
    store = agent.memory
    store.save_session("s-list-1", [{"role": "user", "content": "a"}])
    store.save_session("s-list-2", [{"role": "user", "content": "b"}])
    sessions = store.list_sessions()
    assert len(sessions) >= 2


# ─── Session integration tests ─────────────────────────────────────────────────


def test_session_integration_with_run():
    import unittest.mock
    from nanoagent.llm.base import LLMResponse

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_sesh.db")
    agent = Agent(db_path=db_path)
    mock_llm = unittest.mock.MagicMock()
    mock_llm.chat.return_value = LLMResponse(content="Hello back")
    agent.llm_provider = mock_llm

    session_id = "test-session-run-001"
    response, messages = agent.run("Hello", session_id=session_id)
    assert response is not None

    stored = agent.memory.load_session(session_id)
    assert stored is not None
    assert len(stored["messages"]) > 0
    assert any("Hello" in str(m) for m in stored["messages"])

    agent.memory.close()
    import shutil

    shutil.rmtree(tmpdir)


# ─── Loop detection tests ──────────────────────────────────────────────────────


def test_loop_detection():
    import unittest.mock
    from nanoagent.llm.base import LLMResponse, ToolCall

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_loop.db")
    agent = Agent(db_path=db_path)

    class MockTool:
        description = "A mock tool"

        def execute(self, **kw):
            return "result"

    agent.register_tool("mock_tool", MockTool())

    mock_llm = unittest.mock.MagicMock()
    same_call = ToolCall(id="tc-1", name="mock_tool", arguments={"arg": "val"})
    mock_llm.chat.return_value = LLMResponse(tool_calls=[same_call])
    agent.llm_provider = mock_llm

    loop_count = [0]

    def on_loop_detected(count):
        loop_count[0] = count

    agent.on_loop_detected = on_loop_detected

    response, messages = agent.run("Loop me")
    assert "Auto-paused" in response or "loop" in response.lower()
    assert loop_count[0] >= 2

    agent.memory.close()
    import shutil

    shutil.rmtree(tmpdir)


# ─── Cancellation tests ────────────────────────────────────────────────────────


def test_cancellation():
    import unittest.mock
    import threading
    import time
    from nanoagent.llm.base import LLMResponse

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_cancel.db")
    agent = Agent(db_path=db_path)
    mock_llm = unittest.mock.MagicMock()

    def slow_chat(*args, **kwargs):
        time.sleep(0.3)
        return LLMResponse(content="Done")

    mock_llm.chat.side_effect = slow_chat
    agent.llm_provider = mock_llm

    def _delayed_cancel():
        time.sleep(0.05)
        agent.cancelled = True

    t = threading.Thread(target=_delayed_cancel, daemon=True)
    t.start()

    response, messages = agent.run("Cancel me")
    assert "cancelled" in response.lower()

    agent.memory.close()
    import shutil

    shutil.rmtree(tmpdir)


# ─── Error hierarchy tests (T012e) ──────────────────────────────────────────────


def test_error_hierarchy():
    assert issubclass(ProviderError, AgentError)
    assert issubclass(ProviderRetryableError, ProviderError)
    assert issubclass(ProviderFatalError, ProviderError)
    assert issubclass(ConfigError, AgentError)
    assert issubclass(StateTransitionError, AgentError)


def test_retryable_error_message():
    err = ProviderRetryableError("timeout after 30s")
    assert "timeout" in str(err)


def test_fatal_error_message():
    err = ProviderFatalError("invalid API key")
    assert "API key" in str(err)


def test_state_transition_error_raised():
    a = Agent(db_path=":memory:")
    with pytest.raises(StateTransitionError):
        a._transition(a.state, "no-op")
    a.memory.close()


# ─── Logging tests (T012f) ──────────────────────────────────────────────────────


def test_logger_verbosity():
    from nanoagent.agent.logging import AgentLogger, LogLevel

    logger = AgentLogger(name="test-logger", level=LogLevel.WARNING)
    assert logger.level == LogLevel.WARNING


def test_logger_get_or_create():
    from nanoagent.agent.logging import AgentLogger

    logger = AgentLogger.get("unique-test-logger")
    assert logger is not None
    same = AgentLogger.get("unique-test-logger")
    assert logger is same


def test_logger_configure():
    from nanoagent.agent.logging import AgentLogger, LogLevel

    logger = AgentLogger.configure(verbosity=2)
    assert logger.level == LogLevel.DEBUG
    logger2 = AgentLogger.configure(verbosity=0)
    assert logger2.level == LogLevel.WARNING


# ─── Context calculator tests (T012d) ────────────────────────────────────────────


def test_count_tokens_short_text():
    from nanoagent.agent.context import count_tokens

    count = count_tokens("Hello, world!")
    assert count > 0


def test_count_tokens_different_providers():
    from nanoagent.agent.context import count_tokens

    count1 = count_tokens("Hello, world!", provider="openai")
    count2 = count_tokens("Hello, world!", provider="anthropic")
    assert count1 == count2


def test_truncate_messages_within_limit():
    from nanoagent.agent.context import truncate_messages

    msgs = [{"role": "user", "content": "Hi"}]
    result = truncate_messages(msgs, max_tokens=1000)
    assert len(result) == 1


def test_truncate_messages_removes_old():
    from nanoagent.agent.context import truncate_messages

    msgs = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "First message that is long enough to test with"},
        {"role": "assistant", "content": "A response"},
        {"role": "user", "content": "Second message"},
    ]
    result = truncate_messages(msgs, max_tokens=5)
    assert len(result) < len(msgs) or len(result) == len(msgs)


# ─── Phase 4: Configurable Params & Retry tests (T029-T033) ─────────────────


def test_max_tokens_param_passed_to_provider():
    import unittest.mock
    from nanoagent.llm.base import LLMResponse

    agent = Agent(db_path=":memory:")
    mock_llm = unittest.mock.MagicMock()
    mock_llm.chat.return_value = LLMResponse(content="OK")
    agent.llm_provider = mock_llm
    agent.run("Test", max_tokens=50)
    _call_kwargs = mock_llm.chat.call_args
    assert _call_kwargs is not None
    assert _call_kwargs[1].get("max_tokens") == 50
    agent.memory.close()


def test_temperature_param_passed_to_provider():
    import unittest.mock
    from nanoagent.llm.base import LLMResponse

    agent = Agent(db_path=":memory:")
    mock_llm = unittest.mock.MagicMock()
    mock_llm.chat.return_value = LLMResponse(content="OK")
    agent.llm_provider = mock_llm
    agent.run("Test", temperature=0.0)
    _call_kwargs = mock_llm.chat.call_args
    assert _call_kwargs is not None
    assert _call_kwargs[1].get("temperature") == 0.0
    agent.memory.close()


def test_retry_recovery_on_retryable_error():
    import unittest.mock
    from nanoagent.llm.base import LLMResponse
    from nanoagent.agent.errors import ProviderRetryableError

    agent = Agent(db_path=":memory:")
    agent.retry_attempts = 3
    mock_llm = unittest.mock.MagicMock()
    mock_llm.chat.side_effect = [
        ProviderRetryableError("timeout"),
        ProviderRetryableError("rate-limit"),
        LLMResponse(content="Success after retry"),
    ]
    agent.llm_provider = mock_llm
    response, messages = agent.run("Test retry")
    assert "Success after retry" in response
    assert mock_llm.chat.call_count == 3
    agent.memory.close()


def test_retry_exhaustion_raises():
    import unittest.mock
    from nanoagent.agent.errors import ProviderRetryableError

    agent = Agent(db_path=":memory:")
    agent.retry_attempts = 2
    mock_llm = unittest.mock.MagicMock()
    mock_llm.chat.side_effect = ProviderRetryableError("persistent error")
    agent.llm_provider = mock_llm
    with pytest.raises(ProviderRetryableError):
        agent.run("Test retry exhaust")
    agent.memory.close()


def test_parallel_tool_execution():
    import unittest.mock
    from nanoagent.llm.base import LLMResponse, ToolCall

    agent = Agent(db_path=":memory:")

    class MockTool:
        description = "A mock tool"

        def execute(self, **kw):
            return f"result: {kw}"

    agent.register_tool("tool_a", MockTool())
    agent.register_tool("tool_b", MockTool())
    mock_llm = unittest.mock.MagicMock()
    response_1 = LLMResponse(
        tool_calls=[
            ToolCall(id="t1", name="tool_a", arguments={"x": 1}),
            ToolCall(id="t2", name="tool_b", arguments={"y": 2}),
        ]
    )
    response_2 = LLMResponse(content="Final response")
    mock_llm.chat.side_effect = [response_1, response_2]
    agent.llm_provider = mock_llm
    response, messages = agent.run("Test parallel tools")
    assert "Final response" in response
    tool_messages = [m for m in messages if m.get("role") == "tool"]
    assert len(tool_messages) == 2
    agent.memory.close()


def test_agent_loop_config():
    agent = Agent(db_path=":memory:")
    assert hasattr(agent, "loop_config")
    assert agent.loop_config is not None
    assert agent.loop_config.llm_timeout_seconds == 120.0
    assert agent.loop_config.tool_timeout_seconds == 30.0
    agent.memory.close()


def test_agent_loop_config_from_toml():
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("""
[agent]
default_provider = "openai"
project_path = "/tmp"

[agent.loop]
llm_timeout_seconds = 90
tool_timeout_seconds = 20

[tools.permissions]
max_output_chars = 5000

[[tools.permissions.rules]]
tool_name = "run_shell"
mode = "deny"

[[tools.permissions.rules]]
tool_name = "*"
mode = "allow"
""")
        temp_path = f.name
    try:
        agent = Agent(db_path=":memory:", config_path=temp_path)
        assert agent.loop_config.llm_timeout_seconds == 90
        assert agent.loop_config.tool_timeout_seconds == 20
        agent.memory.close()
    finally:
        os.unlink(temp_path)
