"""Tests for multi-agent delegation (SubAgentManager)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nanoagent.agent.subagent import SubAgentManager, SubAgentTask


AGENT_PATH = "nanoagent.agent.agent.Agent"


@pytest.fixture
def parent_agent():
    agent = MagicMock()
    agent.project_path = "/test/project"
    agent.memory.db_path = "/test/db.sqlite"
    agent.llm_provider = MagicMock()

    tool_web = MagicMock()
    tool_web.name = "web_fetch"
    tool_calc = MagicMock()
    tool_calc.name = "calculator"
    agent.tools = {"web_fetch": tool_web, "calculator": tool_calc}
    return agent


class TestSubAgentManager:
    def test_delegate_single_task(self, parent_agent):
        with patch(AGENT_PATH) as mock_cls:
            child = MagicMock()
            child.run.return_value = (
                "Task completed",
                [{"role": "assistant", "content": "done"}],
            )
            mock_cls.return_value = child

            manager = SubAgentManager(parent_agent)
            task = SubAgentTask(name="test_task", prompt="Do something")
            result = manager.delegate(task)

        assert result.success is True
        assert result.response == "Task completed"
        assert result.name == "test_task"
        assert result.duration_ms > 0
        mock_cls.assert_called_once()

    def test_delegate_all_parallel(self, parent_agent):
        with patch(AGENT_PATH) as mock_cls:
            child = MagicMock()

            def run_side_effect(prompt, **kwargs):
                mapping = {"Do A": "Result A", "Do B": "Result B", "Do C": "Result C"}
                return (mapping.get(prompt, "unknown"), [])

            child.run.side_effect = run_side_effect
            mock_cls.return_value = child

            manager = SubAgentManager(parent_agent)
            tasks = [
                SubAgentTask(name="task_a", prompt="Do A"),
                SubAgentTask(name="task_b", prompt="Do B"),
                SubAgentTask(name="task_c", prompt="Do C"),
            ]
            results = manager.delegate_all(tasks)

        assert len(results) == 3
        result_map = {r.name: r for r in results}
        assert result_map["task_a"].response == "Result A"
        assert result_map["task_b"].response == "Result B"
        assert result_map["task_c"].response == "Result C"
        assert all(r.success for r in results)

    def test_delegate_sequential(self, parent_agent):
        with patch(AGENT_PATH) as mock_cls:
            child_a = MagicMock()
            child_a.run.return_value = ("First", [])
            child_b = MagicMock()
            child_b.run.return_value = ("Second", [])
            mock_cls.side_effect = [child_a, child_b]

            manager = SubAgentManager(parent_agent)
            tasks = [
                SubAgentTask(name="first", prompt="Do first"),
                SubAgentTask(name="second", prompt="Do second"),
            ]
            results = manager.delegate_sequential(tasks)

        assert len(results) == 2
        assert results[0].name == "first"
        assert results[1].name == "second"

    def test_tool_filtering(self, parent_agent):
        with patch(AGENT_PATH) as mock_cls:
            child = MagicMock()
            child.run.return_value = ("Done", [])
            mock_cls.return_value = child

            manager = SubAgentManager(parent_agent)
            task = SubAgentTask(name="web_only", prompt="Search", tools=["web_fetch"])
            manager.delegate(task)

        call_args = child.register_tool.call_args_list
        tool_names = [args[0][0] for args in call_args]
        assert "web_fetch" in tool_names
        assert "calculator" not in tool_names

    def test_tool_no_filter_all_tools(self, parent_agent):
        with patch(AGENT_PATH) as mock_cls:
            child = MagicMock()
            child.run.return_value = ("Done", [])
            mock_cls.return_value = child

            manager = SubAgentManager(parent_agent)
            task = SubAgentTask(name="all_tools", prompt="Do everything")
            manager.delegate(task)

        call_args = child.register_tool.call_args_list
        tool_names = [args[0][0] for args in call_args]
        assert "web_fetch" in tool_names
        assert "calculator" in tool_names

    def test_error_handling(self, parent_agent):
        with patch(AGENT_PATH) as mock_cls:
            child = MagicMock()
            child.run.side_effect = RuntimeError("Something went wrong")
            mock_cls.return_value = child

            manager = SubAgentManager(parent_agent)
            task = SubAgentTask(name="failing", prompt="This will fail")
            result = manager.delegate(task)

        assert result.success is False
        assert "Something went wrong" in result.error
        assert result.response == ""

    def test_empty_task_list(self, parent_agent):
        manager = SubAgentManager(parent_agent)
        assert manager.delegate_all([]) == []
        assert manager.delegate_sequential([]) == []

    def test_result_storage(self, parent_agent):
        with patch(AGENT_PATH) as mock_cls:
            child = MagicMock()
            child.run.return_value = ("Stored", [])
            mock_cls.return_value = child

            manager = SubAgentManager(parent_agent)
            manager.delegate(SubAgentTask(name="stored_task", prompt="Store me"))

        result = manager.get_result("stored_task")
        assert result is not None
        assert result.success is True
        assert "stored_task" in manager.all_results()

    def test_clear_results(self, parent_agent):
        with patch(AGENT_PATH) as mock_cls:
            child = MagicMock()
            child.run.return_value = ("Clear me", [])
            mock_cls.return_value = child

            manager = SubAgentManager(parent_agent)
            manager.delegate(SubAgentTask(name="clear_me", prompt="Test"))
            assert len(manager.all_results()) == 1
            manager.clear_results()
            assert len(manager.all_results()) == 0

    def test_agent_without_provider(self, parent_agent):
        parent_no_provider = MagicMock()
        parent_no_provider.project_path = None
        parent_no_provider.memory.db_path = None
        parent_no_provider.llm_provider = None
        parent_no_provider.tools = {}

        with patch(AGENT_PATH) as mock_cls:
            child = MagicMock()
            child.run.return_value = ("echo response", [])
            mock_cls.return_value = child

            manager = SubAgentManager(parent_no_provider)
            task = SubAgentTask(name="echo", prompt="hello")
            result = manager.delegate(task)
            assert result.success is True
