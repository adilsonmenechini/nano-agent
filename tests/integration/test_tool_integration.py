"""Integration tests for tool system: permissions + truncation + registry."""
from __future__ import annotations

from nanoagent.permissions import PermissionManager, PermissionRule, PermissionMode
from nanoagent.registry import ToolRegistry
from nanoagent.truncation import OutputTruncator


def test_tool_registry_with_permissions_and_truncation():
    """PermissionManager + OutputTruncator + ToolRegistry work together."""
    pm = PermissionManager(default_mode="allow")
    pm.add_rule(PermissionRule(
        tool_name="run_shell", match_type="prefix", pattern="rm", mode=PermissionMode.DENY,
    ))
    trunc = OutputTruncator(max_chars=10)
    registry = ToolRegistry(permission_manager=pm, output_truncator=trunc)

    from nanoagent.tool import Tool

    @Tool
    def run_shell(command: str) -> str:
        return f"executed: {command}"

    registry.register(run_shell)

    allowed = registry.execute("run_shell", {"command": "echo hello"})
    assert "executed" in allowed

    denied = registry.execute("run_shell", {"command": "rm -rf /"})
    assert "permission denied" in denied.lower()

    truncated = registry.execute("run_shell", {"command": "a" * 200})
    assert "[truncated" in truncated


def test_permission_manager_blocks_denied_tools():
    pm = PermissionManager(default_mode="allow")
    pm.add_rule(PermissionRule(
        tool_name="run_shell", match_type="prefix", pattern="sudo", mode=PermissionMode.DENY,
    ))
    registry = ToolRegistry(permission_manager=pm)

    from nanoagent.tool import Tool

    @Tool
    def run_shell(command: str) -> str:
        return f"ran: {command}"

    registry.register(run_shell)

    result = registry.execute("run_shell", {"command": "sudo echo hi"})
    assert "permission denied" in result.lower()


def test_output_truncation_applied_through_registry():
    trunc = OutputTruncator(max_chars=5)
    registry = ToolRegistry(output_truncator=trunc)

    def greet(name: str) -> str:
        return f"Hello, {name}!"

    registry.register(greet)

    result = registry.execute("greet", {"name": "World"})
    assert "[truncated" in result


def test_default_truncator_passthrough():
    registry = ToolRegistry()

    def echo(msg: str) -> str:
        return msg

    registry.register(echo)

    result = registry.execute("echo", {"msg": "short"})
    assert result == "short"
