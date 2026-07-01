"""Edge-case tests for CLI entry points and utility functions."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from click.testing import CliRunner


from nanoagent.cli import (
    _build_system_prompt,
    _fmt_time,
    _handle_memory_insights,
    _handle_memory_search,
    _print_full_help,
    _print_welcome,
    _stdin_ready,
    cli,
)


class TestCliRunner:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "nanoagent" in result.output.lower() or "usage" in result.output.lower()

    def test_health_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["health", "--help"])
        assert result.exit_code == 0

    def test_check_config_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["check-config", "--help"])
        assert result.exit_code == 0


class TestCliUtilities:
    def test_fmt_time(self):
        assert isinstance(_fmt_time(0), str)
        assert len(_fmt_time(0)) > 0

    def test_stdin_ready_nontty(self):
        result = _stdin_ready(timeout=0)
        assert isinstance(result, bool)

    def test_print_welcome_no_raise(self):
        _print_welcome()

    def test_print_full_help_no_raise(self):
        _print_full_help()


class TestBuildSystemPrompt:
    def test_none_returns_none(self):
        assert _build_system_prompt(None) is None
        assert _build_system_prompt("") is None

    def test_no_files_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            assert _build_system_prompt(d) is None

    def test_with_agent_md(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "AGENT.md").write_text("You are helpful.")
            result = _build_system_prompt(d)
            assert result is not None
            assert "helpful" in result

    def test_with_user_md(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "USER.md").write_text("User preference here.")
            result = _build_system_prompt(d)
            assert result is not None
            assert "User preference" in result

    def test_both_files_joined(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "AGENT.md").write_text("Agent content")
            Path(d, "USER.md").write_text("User content")
            result = _build_system_prompt(d)
            assert "Agent content" in result
            assert "User content" in result


class TestHandleMemorySearch:
    def test_no_results(self):
        agent = MagicMock()
        agent.memory.search.return_value = []
        _handle_memory_search("test", agent)

    def test_with_results(self):
        agent = MagicMock()
        row = MagicMock()
        row.target = "memory"
        row.content = "some content here"
        row.key = "test_key"
        agent.memory.search.return_value = [row]
        _handle_memory_search("test", agent)


class TestHandleMemoryInsights:
    def test_no_memories(self):
        agent = MagicMock()
        agent.memory.conn.execute.return_value.fetchall.return_value = []
        _handle_memory_insights(agent)

    def test_with_memories(self):
        agent = MagicMock()
        r = MagicMock()
        r.__getitem__ = lambda s, k: {
            "target": "memory",
            "cnt": 5,
            "oldest": 0,
            "newest": 100,
        }[k]
        agent.memory.conn.execute.return_value.fetchall.return_value = [r]
        _handle_memory_insights(agent)
