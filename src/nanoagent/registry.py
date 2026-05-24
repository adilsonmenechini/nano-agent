from __future__ import annotations

from collections.abc import Callable

from nanoagent.tool import Tool, tool as _tool_decorator


class ToolRegistry:

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, t: Tool | Callable, *, name: str | None = None, description: str | None = None) -> Tool:
        if isinstance(t, Tool):
            self._tools[t.name] = t
            return t
        t_obj = _tool_decorator(t, name=name, description=description)
        self._tools[t_obj.name] = t_obj
        return t_obj

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def remove(self, name: str) -> None:
        self._tools.pop(name, None)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def openai_schemas(self) -> list[dict]:
        return [t.schema for t in self._tools.values()]

    def anthropic_schemas(self) -> list[dict]:
        return [t.anthropic_schema for t in self._tools.values()]

    def execute(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: unknown tool '{name}'"
        try:
            result = tool(**arguments)
            return str(result) if result is not None else ""
        except Exception as e:
            return f"Error executing {name}: {e}"
