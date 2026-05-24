from __future__ import annotations

import inspect
from typing import Any

from nanoagent.tool import Tool, py_to_json_schema
from nanoagent.registry import ToolRegistry
from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.skills.skill_storage import SkillStorage


def _from_legacy_tool(tool_obj: Any, name: str) -> Tool:
    desc = getattr(tool_obj, "description", "") or ""
    execute = tool_obj.execute
    try:
        sig = inspect.signature(execute)
        params = [p for p in sig.parameters.values() if p.name != "self"]
        hints = {k: v for k, v in (getattr(execute, "__annotations__", {}) or {}).items() if k != "self" and k != "return"}
        schema = {"type": "object", "properties": {}, "required": []}
        for p in params:
            tp = hints.get(p.name, str)
            prop = py_to_json_schema(tp)
            if p.default is inspect.Parameter.empty:
                schema["required"].append(p.name)
            elif p.default is not None:
                prop["default"] = p.default
            schema["properties"][p.name] = prop
        t = Tool.__new__(Tool)
        t.name = name
        t.description = desc
        t.fn = lambda **kw: execute(**kw)
        t.parameters = schema
        return t
    except Exception:
        t = Tool.__new__(Tool)
        t.name = name
        t.description = desc
        t.fn = lambda **kw: execute(**kw)
        t.parameters = {"type": "object", "properties": {}}
        return t


class Agent:

    def __init__(self, project_path: str | None = None, db_path: str | None = None, llm_provider: Any = None):
        self._tools = ToolRegistry()
        self._legacy_tools: dict[str, Any] = {}
        self._skills: dict[str, Any] = {}
        self.memory = SQLiteMemoryStore(db_path=db_path)
        self.project_path = project_path
        self.llm_provider = llm_provider
        self.skill_storage = SkillStorage(db_path=db_path)

    @property
    def tools(self) -> dict[str, Any]:
        result = dict(self._legacy_tools)
        for t in self._tools.all():
            if t.name not in result:
                result[t.name] = t
        return result

    @property
    def skills(self) -> dict[str, Any]:
        return dict(self._skills)

    def register_tool(self, name: str, tool_obj: Any) -> None:
        if hasattr(tool_obj, "execute"):
            t = _from_legacy_tool(tool_obj, name)
            self._tools.register(t)
            self._legacy_tools[name] = tool_obj
        else:
            self._tools.register(tool_obj, name=name)

    def execute_tool(self, name: str, arguments: dict) -> str:
        return self._tools.execute(name, arguments)

    def tool_schemas(self, provider: str = "openai") -> list[dict]:
        if provider == "anthropic":
            return self._tools.anthropic_schemas()
        return self._tools.openai_schemas()

    def register_skill(self, name: str, skill_obj: Any) -> None:
        self._skills[name] = skill_obj

    def execute_skill(self, name: str, **kwargs) -> Any:
        skill = self._skills.get(name)
        if not skill:
            raise ValueError(f"Skill '{name}' not found")
        return skill.execute(**kwargs) if hasattr(skill, "execute") else skill(**kwargs)

    def remember(self, key: str, value: str, target: str = "memory", scope: str = "global", category: str | None = None):
        self.memory.add(target=target, scope=scope, key=key, value=value, category=category,
                        project_path=self.project_path if scope == "project" else None)

    def recall(self, key: str, target: str = "memory", scope: str = "global") -> str | None:
        return self.memory.get(target=target, scope=scope, key=key,
                               project_path=self.project_path if scope == "project" else None)

    def run(self, prompt: str, system_prompt: str | None = None, max_iterations: int = 10,
            messages: list[dict] | None = None) -> tuple[str, list[dict]]:
        if not self.llm_provider:
            return f"Agent received: {prompt}", []

        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        else:
            messages.append({"role": "user", "content": prompt})

        tools = self._tools.openai_schemas()

        for _ in range(max_iterations):
            response = self.llm_provider.chat(
                messages=messages,
                tools=tools if tools else None,
                system_prompt=system_prompt,
            )

            if response.tool_calls:
                for tc in response.tool_calls:
                    result = self.execute_tool(tc.name, tc.arguments)
                    messages.append({"role": "assistant", "content": None, "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": str(tc.arguments)}}]})
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            else:
                messages.append({"role": "assistant", "content": response.content or ""})
                return response.content or "", messages
        messages.append({"role": "assistant", "content": "Max iterations reached."})
        return "Max iterations reached.", messages
