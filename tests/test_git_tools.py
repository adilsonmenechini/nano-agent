import os
import tempfile

import pytest

from nanoagent.registry import ToolRegistry


def _git_init(path):
    os.system(f"git init {path} >/dev/null 2>&1")
    os.system(f"git -C {path} config user.email test@test.com")
    os.system(f"git -C {path} config user.name test")


def _git_commit(path, msg="initial"):
    os.system(f"git -C {path} add -A >/dev/null 2>&1")
    os.system(f"git -C {path} commit -m '{msg}' >/dev/null 2>&1")


class TestGitTools:
    def test_git_status(self):
        from nanoagent.agent.tools.git_tools import git_status
        with tempfile.TemporaryDirectory() as tmpdir:
            _git_init(tmpdir)
            open(os.path.join(tmpdir, "newfile.txt"), "w").close()
            result = git_status(path=tmpdir)
            assert "newfile.txt" in result

    def test_git_diff(self):
        from nanoagent.agent.tools.git_tools import git_diff
        with tempfile.TemporaryDirectory() as tmpdir:
            _git_init(tmpdir)
            fpath = os.path.join(tmpdir, "file.txt")
            with open(fpath, "w") as f:
                f.write("original")
            _git_commit(tmpdir, "first")
            with open(fpath, "w") as f:
                f.write("modified")
            result = git_diff(path=tmpdir)
            assert "modified" in result or "original" in result or "-original" in result or "+modified" in result

    def test_git_log(self):
        from nanoagent.agent.tools.git_tools import git_log
        with tempfile.TemporaryDirectory() as tmpdir:
            _git_init(tmpdir)
            open(os.path.join(tmpdir, "f1.txt"), "w").close()
            _git_commit(tmpdir, "first commit")
            open(os.path.join(tmpdir, "f2.txt"), "w").close()
            _git_commit(tmpdir, "second commit")
            result = git_log(path=tmpdir, max_count=5)
            assert "first commit" in result
            assert "second commit" in result

    def test_git_log_max_count(self):
        from nanoagent.agent.tools.git_tools import git_log
        with tempfile.TemporaryDirectory() as tmpdir:
            _git_init(tmpdir)
            for i in range(5):
                open(os.path.join(tmpdir, f"f{i}.txt"), "w").close()
                _git_commit(tmpdir, f"commit {i}")
            result = git_log(path=tmpdir, max_count=2)
            lines = [l for l in result.strip().split("\n") if l.strip()]
            assert len(lines) <= 2

    def test_non_git_directory(self):
        from nanoagent.agent.tools.git_tools import git_status
        with tempfile.TemporaryDirectory() as tmpdir:
            result = git_status(path=tmpdir)
            assert "error" in result.lower() or "not a git" in result.lower()

    def test_git_not_installed(self, monkeypatch):
        from nanoagent.agent.tools.git_tools import git_status
        monkeypatch.setenv("PATH", "")
        result = git_status(path=".")
        assert "error" in result.lower() or "not found" in result.lower()

    def test_registers_in_tool_registry(self):
        from nanoagent.agent.tools.git_tools import git_status, git_diff, git_log
        registry = ToolRegistry()
        registry.register(git_status)
        registry.register(git_diff)
        registry.register(git_log)
        assert registry.get("git_status") is not None
        assert registry.get("git_diff") is not None
        assert registry.get("git_log") is not None
