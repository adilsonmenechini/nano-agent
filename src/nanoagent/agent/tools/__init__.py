"""Built-in tool functions for the agent.

Tools are defined using the @tool decorator pattern from nanoagent/tool.py.
Each tool function has type-hint-inferred JSON Schema for LLM consumption.
"""

from __future__ import annotations

from nanoagent.registry import ToolRegistry


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Register all built-in tools into the given ToolRegistry.

    Args:
        registry: A ToolRegistry instance to register tools into.
    """
    try:
        from nanoagent.agent.tools.shell import run_shell
        registry.register(run_shell)
    except ImportError:
        pass

    try:
        from nanoagent.agent.tools.file_tools import read_file, write_file, glob_file, grep_file
        registry.register(read_file)
        registry.register(write_file)
        registry.register(glob_file)
        registry.register(grep_file)
    except ImportError:
        pass

    try:
        from nanoagent.agent.tools.git_tools import git_status, git_diff, git_log
        registry.register(git_status)
        registry.register(git_diff)
        registry.register(git_log)
    except ImportError:
        pass


__all__ = ["register_builtin_tools"]
