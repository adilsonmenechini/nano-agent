
from nanoagent.registry import ToolRegistry


class TestShellTool:
    def test_basic_execution(self):
        from nanoagent.agent.tools.shell import run_shell

        result = run_shell(command="echo hello")
        assert "hello" in result

    def test_non_zero_exit(self):
        from nanoagent.agent.tools.shell import run_shell

        result = run_shell(command="false")
        assert "exit code" in result.lower() or "1" in result

    def test_command_timeout(self):
        from nanoagent.agent.tools.shell import run_shell

        result = run_shell(command="sleep 10", timeout=1)
        assert "tim" in result.lower()

    def test_empty_command(self):
        from nanoagent.agent.tools.shell import run_shell

        result = run_shell(command="")
        assert "error" in result.lower() or "empty" in result.lower()

    def test_working_directory(self):
        from nanoagent.agent.tools.shell import run_shell
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_shell(command="pwd", workdir=tmpdir)
            assert tmpdir in result

    def test_registers_in_tool_registry(self):
        from nanoagent.agent.tools.shell import run_shell

        registry = ToolRegistry()
        registry.register(run_shell)
        result = registry.execute("run_shell", {"command": "echo hello"})
        assert "hello" in result
