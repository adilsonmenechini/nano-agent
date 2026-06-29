from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from nanoagent.tool import Tool, tool as _tool_decorator

if TYPE_CHECKING:
    from nanoagent.permissions import PermissionManager
    from nanoagent.truncation import OutputTruncator


class ToolRegistry:
    def __init__(
        self,
        permission_manager: PermissionManager | None = None,
        output_truncator: OutputTruncator | None = None,
    ):
        self._tools: dict[str, Tool] = {}
        self._permission_manager = permission_manager
        self._output_truncator = output_truncator

    def register(
        self,
        t: Tool | Callable,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Tool:
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

        command = arguments.get("command", "")
        if self._permission_manager:
            result = self._permission_manager.check(name, command)
            if result is not None:
                from nanoagent.permissions import PermissionMode
                if result == PermissionMode.DENY:
                    return f"Error: permission denied for tool '{name}'"
                elif result == PermissionMode.ASK:
                    return f"Error: tool '{name}' requires human approval"

        try:
            output = tool(**arguments)
            result = str(output) if output is not None else ""
            if self._output_truncator:
                result = self._output_truncator.truncate(result)
            return result
        except PermissionError as e:
            return f"Error: {e}"
        except FileNotFoundError as e:
            return f"Error: {e}"
        except IsADirectoryError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error executing {name}: {e}"

    def execute_parallel(self, calls: list[tuple[str, dict]]) -> list[str]:
        results: list[str] = [""] * len(calls)
        with ThreadPoolExecutor(max_workers=min(len(calls), 4)) as pool:
            fut_map = {
                pool.submit(self.execute, name, args): i
                for i, (name, args) in enumerate(calls)
            }
            for fut in as_completed(fut_map):
                idx = fut_map[fut]
                try:
                    results[idx] = fut.result()
                except Exception as e:
                    results[idx] = f"Error: {e}"
        return results
