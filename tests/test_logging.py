"""Tests for AgentLogger."""
import io

from nanoagent.agent.logging import AgentLogger, LogLevel


class TestAgentLogger:
    def test_basic_logging(self):
        stream = io.StringIO()
        logger = AgentLogger("test_basic", level=LogLevel.DEBUG, stream=stream)
        logger.debug("debug msg")
        logger.info("info msg")
        logger.warning("warn msg")
        logger.error("error msg")
        output = stream.getvalue()
        assert "debug msg" in output
        assert "info msg" in output
        assert "warn msg" in output
        assert "error msg" in output

    def test_state_transition(self):
        stream = io.StringIO()
        logger = AgentLogger("test_state", level=LogLevel.INFO, stream=stream)
        logger.state_transition("IDLE", "THINKING", "user input")
        assert "STATE" in stream.getvalue()
        assert "IDLE -> THINKING" in stream.getvalue()

    def test_tool_call(self):
        stream = io.StringIO()
        logger = AgentLogger("test_tool", level=LogLevel.DEBUG, stream=stream)
        logger.tool_call("web_search", {"q": "test"})
        assert "TOOL" in stream.getvalue()

    def test_llm_request(self):
        stream = io.StringIO()
        logger = AgentLogger("test_llm", level=LogLevel.DEBUG, stream=stream)
        logger.llm_request("gpt-4", 150)
        assert "LLM" in stream.getvalue()

    def test_level_property(self):
        logger = AgentLogger("test_level", level=LogLevel.WARNING)
        assert logger.level == LogLevel.WARNING

    def test_get_singleton(self):
        logger1 = AgentLogger.get("test_singleton")
        logger2 = AgentLogger.get("test_singleton")
        assert logger1 is logger2

    def test_configure(self):
        logger = AgentLogger.configure(verbosity=2, name="test_configure")
        assert logger.level == LogLevel.DEBUG

    def test_configure_default(self):
        logger = AgentLogger.configure(verbosity=99)
        assert logger.level == LogLevel.WARNING

    def test_verbosity_levels(self):
        v0 = AgentLogger.configure(verbosity=0, name="v0")
        assert v0.level == LogLevel.WARNING
        v1 = AgentLogger.configure(verbosity=1, name="v1")
        assert v1.level == LogLevel.INFO
        v2 = AgentLogger.configure(verbosity=2, name="v2")
        assert v2.level == LogLevel.DEBUG
