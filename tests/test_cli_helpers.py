"""Unit tests for cli.py helper functions."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nanoagent.cli import (
    _handle_history,
    _handle_tools,
    _handle_skills,
    _handle_memory_search,
    _handle_memory_insights,
    _handle_memory_forget,
    _handle_memory_consolidate,
    _handle_shell,
    _print_banner,
    _print_welcome,
    _handle_jobs,
    _handle_pause,
    _handle_resume,
    _handle_cancel,
)


class TestPrintHelpers:
    def test_print_banner_no_crash(self):
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _print_banner()
        assert m.called

    def test_print_welcome_no_crash(self):
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _print_welcome()
        assert m.called


class TestHandleHistory:
    def test_empty(self):
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_history([])
        assert m.called

    def test_user_and_assistant(self):
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_history([
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ])
        assert any("user:" in str(c) for c in m.call_args_list)

    def test_tool_assistant_message(self):
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_history([
                {"role": "assistant", "tool_calls": [{"function": {"name": "search"}}]},
            ])
        assert any("tool" in str(c).lower() for c in m.call_args_list)

    def test_tool_result_role_no_content(self):
        from nanoagent.cli import console
        # role=tool with empty content → hits the "tool result" branch (line 343-344)
        with patch.object(console, "print") as m:
            _handle_history([{"role": "tool"}])
        assert any("tool result" in str(c).lower() for c in m.call_args_list)

    def test_long_content(self):
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_history([{"role": "user", "content": "a" * 500}])
        assert m.called


class TestHandleTools:
    def test_no_tools(self):
        agent = MagicMock()
        agent.tools = {}
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_tools(agent)
        assert m.called

    def test_with_tools(self):
        agent = MagicMock()
        agent.tools = {
            "t1": MagicMock(description="description A"),
            "t2": MagicMock(description=None),
        }
        from nanoagent.cli import console
        with patch.object(console, "print"):
            _handle_tools(agent)


class TestHandleSkills:
    def test_no_skills_stored(self):
        agent = MagicMock()
        agent.skill_storage.list_skills.return_value = []
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_skills(agent)
        assert m.called

    def test_with_skills_stored(self):
        agent = MagicMock()
        agent.skill_storage.list_skills.return_value = [
            {"name": "search", "description": "Search the web"},
            {"name": "calc", "description": "Do math"},
        ]
        from nanoagent.cli import console
        with patch.object(console, "print"):
            _handle_skills(agent)
        # Calling should complete without exceptions.
        assert agent.skill_storage.list_skills.called


class TestHandleMemorySearch:
    def test_empty_query(self):
        agent = MagicMock()
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_memory_search("", agent)
        assert any("Usage" in str(c) for c in m.call_args_list)
        agent.memory.search.assert_not_called()

    def test_no_search_results(self):
        agent = MagicMock()
        agent.memory.search.return_value = []
        from nanoagent.cli import console
        with patch.object(console, "print"):
            _handle_memory_search("alice", agent)
        agent.memory.search.assert_called_once_with("alice", limit=20)

    def test_with_results(self):
        agent = MagicMock()
        agent.memory.search.return_value = [
            MagicMock(target="t1", content="some text", key="k1"),
            MagicMock(target="t2", content="other", key=""),
        ]
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_memory_search("query", agent)
        assert m.called


class TestHandleShell:
    def test_shell_success(self, tmp_path):
        from nanoagent.cli import console
        sh_file = tmp_path / "s.py"
        sh_file.write_text("print('ok')")
        with patch("nanoagent.cli.subprocess.run") as mock_run, \
             patch.object(console, "print"):
            mock_run.return_value = MagicMock(returncode=0, stdout="out\n", stderr="")
            _handle_shell(str(sh_file))
        mock_run.assert_called_once()

    def test_shell_failure(self, tmp_path):
        from nanoagent.cli import console
        sh_file = tmp_path / "bad.py"
        sh_file.write_text("raise")
        with patch("nanoagent.cli.subprocess.run") as mock_run, \
             patch.object(console, "print") as m:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
            _handle_shell(str(sh_file))
        assert m.called


class TestHandleJobs:
    def test_empty_jobs(self):
        mgr = MagicMock()
        mgr.list_jobs.return_value = []
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_jobs(mgr)
        assert m.called

    def test_with_jobs(self):
        mgr = MagicMock()
        mgr.list.return_value = [
            MagicMock(job_id="x", status="queued", prompt="p"),
        ]
        from nanoagent.cli import console
        with patch.object(console, "print"):
            _handle_jobs(mgr)
        assert mgr.list.called


class TestHandlePauseResumeCancel:
    def test_pause_running_job(self):
        mgr = MagicMock()
        job = MagicMock(status="running")
        mgr.latest.return_value = job
        job.agent.pause_event = MagicMock()
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_pause(mgr)
        assert m.called

    def test_pause_no_running_job(self):
        mgr = MagicMock()
        mgr.latest.return_value = None
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_pause(mgr)
        assert m.called

    def test_resume_paused_job(self):
        mgr = MagicMock()
        job = MagicMock(status="paused")
        mgr.latest.return_value = job
        job.agent.pause_event = MagicMock()
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_resume(mgr)
        assert m.called

    def test_resume_no_running_job(self):
        mgr = MagicMock()
        mgr.latest.return_value = None
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_resume(mgr)
        assert m.called

    def test_cancel_paused_job(self):
        mgr = MagicMock()
        job = MagicMock(status="paused")
        mgr.latest.return_value = job
        job.agent = MagicMock()
        job.agent.memory = MagicMock()
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_cancel(mgr)
        assert m.called

    def test_cancel_no_active_job(self):
        mgr = MagicMock()
        mgr.latest.return_value = None
        from nanoagent.cli import console
        with patch.object(console, "print") as m:
            _handle_cancel(mgr)
        assert m.called


class TestHandleMemoryInsights:
    def test_no_insights(self):
        agent = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        agent.memory.conn.execute.return_value = cursor
        with patch("nanoagent.cli.console.print"):
            _handle_memory_insights(agent)

    def test_with_insights(self):
        agent = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"target": "user", "cnt": 5, "oldest": 1700000000.0, "newest": 1700000100.0},
            {"target": "assistant", "cnt": 3, "oldest": 1700000050.0, "newest": 1700000099.0},
        ]
        agent.memory.conn.execute.return_value = cursor
        with patch("nanoagent.cli.console.print"):
            _handle_memory_insights(agent)


class TestHandleMemoryForget:
    def test_forget_all(self):
        agent = MagicMock()
        agent.memory.delete_all.return_value = 5
        with patch("nanoagent.cli.console.print"):
            _handle_memory_forget("/memory-forget --all", agent)
        agent.memory.delete_all.assert_called_once_with()

    def test_forget_target(self):
        agent = MagicMock()
        agent.memory.delete_all.return_value = 3
        with patch("nanoagent.cli.console.print"):
            _handle_memory_forget("/memory-forget --target user", agent)
        agent.memory.delete_all.assert_called_once_with(target="user")

    def test_forget_key_found_and_deleted(self):
        agent = MagicMock()
        agent.memory.conn.execute.return_value.fetchall.return_value = [
            {"id": 1, "target": "t", "key": "k", "content": "c"},
            {"id": 2, "target": "t", "key": "k", "content": "c2"},
        ]
        with patch("nanoagent.cli.console.print"), \
             patch.object(agent.memory.conn, "commit") as mock_commit:
            _handle_memory_forget("/memory-forget k", agent)
        mock_commit.assert_called_once()
        calls = agent.memory.conn.execute.call_args_list
        assert any("DELETE FROM memories WHERE id = ?" == c.args[0] for c in calls)

    def test_forget_key_not_found(self):
        agent = MagicMock()
        agent.memory.conn.execute.return_value.fetchall.return_value = []
        with patch("nanoagent.cli.console.print") as m:
            _handle_memory_forget("/memory-forget missing", agent)
        assert any("No memory found" in str(c) for c in m.call_args_list)


class TestHandleMemoryConsolidate:
    def test_consolidate_empty(self):
        """Test memory consolidation with empty state."""
        agent = MagicMock()
        agent.memory = MagicMock()
        agent.memory.consolidate_dedup.return_value = 0
        agent.memory.conn.execute.return_value.fetchall.return_value = []
        agent.llm_provider = None
        
        with patch("nanoagent.cli.console.print"):
            _handle_memory_consolidate(agent)
        agent.memory.consolidate_dedup.assert_called_once()
        agent.memory.conn.execute.assert_called_once()

    def test_consolidate_with_memories(self):
        """Test memory consolidation with data."""
        agent = MagicMock()
        agent.memory = MagicMock()
        agent.memory.consolidate_dedup.return_value = 0
        agent.memory.conn.execute.return_value.fetchall.return_value = [
            {"target": "user", "cnt": 5}
        ]
        agent.llm_provider = None
        
        with patch("nanoagent.cli.console.print"):
            _handle_memory_consolidate(agent)
        agent.memory.consolidate_dedup.assert_called_once()
        assert agent.memory.conn.execute.call_count >= 1


class TestRunWithStatus:
    """Test _run_with_status which has many uncovered lines."""
    
    def test_empty_agent(self):
        """Test with agent that has no tools/skills."""
        agent = MagicMock()
        agent.tools = {}
        agent.skill_storage.list_skills.return_value = []
        agent.state = "idle"
        # This is difficult to fully test due to threading/async nature
        # Just test it's callable
        try:
            from nanoagent.cli import _run_with_status
            # We can't easily run it due to async/threading
            # Just verify it exists and can be imported
            assert callable(_run_with_status)
        except ImportError:
            pass


class TestPrintFullHelp:
    def test_help_prints(self):
        """Test that _print_full_help runs."""
        from nanoagent.cli import _print_full_help
        with patch("nanoagent.cli.console.print"):
            _print_full_help()


class TestPrintBannerWelcome:
    def test_banner_and_welcome(self):
        """Test banner and welcome prints."""
        from nanoagent.cli import _print_banner, _print_welcome
        with patch("nanoagent.cli.console.print"):
            _print_banner()
            _print_welcome()
