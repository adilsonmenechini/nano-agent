from __future__ import annotations

import inspect
import json
import threading
import uuid
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
        hints = {
            k: v
            for k, v in (getattr(execute, "__annotations__", {}) or {}).items()
            if k != "self" and k != "return"
        }
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
    def __init__(
        self,
        project_path: str | None = None,
        db_path: str | None = None,
        llm_provider: Any = None,
    ):
        self._tools = ToolRegistry()
        self._legacy_tools: dict[str, Any] = {}
        self._skills: dict[str, Any] = {}
        self.memory = SQLiteMemoryStore(db_path=db_path)
        self.project_path = project_path
        self.llm_provider = llm_provider
        self.skill_storage = SkillStorage(db_path=db_path, store=self.memory)

        # ── Execution control ──────────────────────────────────────────────
        self.cancelled = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.loop_warning_count = 0
        self._prev_tool_sigs: list[tuple[str, str]] | None = None

        # ── Callbacks ──────────────────────────────────────────────────────
        # on_thinking()              → called before each LLM request
        # on_tool_call(name, args)   → called before a tool is executed
        # on_tool_result(name, res)  → called after a tool returns
        # on_skill_call(name, args)  → called before a skill is executed
        # on_skill_result(name, res) → called after a skill returns
        self.on_thinking: Any = None
        self.on_tool_call: Any = None
        self.on_tool_result: Any = None
        self.on_skill_call: Any = None
        self.on_skill_result: Any = None
        self.on_paused: Any = None
        self.on_cancelled: Any = None
        self.on_loop_detected: Any = None

        from nanoagent.config import AgentConfig

        config = AgentConfig()
        self.review_enabled = config.review_enabled
        self.flush_min_turns = config.flush_min_turns
        self.nudge_interval = config.nudge_interval
        self.nudge_tool_calls = config.nudge_tool_calls

        self.background_review = None
        if self.review_enabled:
            from nanoagent.memory.background_review import BackgroundReview

            self.background_review = BackgroundReview(
                self,
                nudge_interval=self.nudge_interval,
                nudge_tool_calls=self.nudge_tool_calls,
            )

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
        if self.on_skill_call:
            self.on_skill_call(name, kwargs)
        res = skill.execute(**kwargs) if hasattr(skill, "execute") else skill(**kwargs)
        if self.on_skill_result:
            self.on_skill_result(name, res)
        return res

    def remember(
        self,
        key: str,
        value: str,
        target: str = "memory",
        scope: str = "global",
        category: str | None = None,
    ):
        self.memory.add(
            target=target,
            scope=scope,
            key=key,
            value=value,
            category=category,
            project_path=self.project_path if scope == "project" else None,
        )

    def recall(
        self, key: str, target: str = "memory", scope: str = "global"
    ) -> str | None:
        return self.memory.get(
            target=target,
            scope=scope,
            key=key,
            project_path=self.project_path if scope == "project" else None,
        )

    def build_system_prompt(
        self,
        base_prompt: str | None = None,
        inject_memory: bool = True,
        inject_failures: bool = True,
    ) -> str:
        """Construct the rich system prompt injecting memory context and policy."""
        from nanoagent.memory.constants import MEMORY_POLICY_PROMPT

        parts = []
        if base_prompt:
            parts.append(base_prompt)

        parts.append(MEMORY_POLICY_PROMPT)

        if inject_memory:
            # 1. User profile memories
            user_context = self.memory.format_for_system_prompt("user")
            if user_context:
                parts.append(f"<user-profile>\n{user_context}\n</user-profile>")

            # 2. General/Global memories
            global_memories = self.memory.format_for_system_prompt("memory")

            # 3. Project memories
            project_memories = ""
            if self.project_path:
                project_memories = self.memory.format_project_block(
                    "memory", self.project_path
                )

            if global_memories or project_memories:
                memory_block = []
                if global_memories:
                    memory_block.append(f"Global Memories:\n{global_memories}")
                if project_memories:
                    memory_block.append(f"Project Memories:\n{project_memories}")
                parts.append("<memory>\n" + "\n\n".join(memory_block) + "\n</memory>")

        if inject_failures:
            failures = self.memory.search_failures(
                project_path=self.project_path, limit=5
            )
            if failures:
                failures_str = []
                for f in failures:
                    failures_str.append(f"[{f.category or 'failure'}] {f.content}")
                parts.append(
                    "<recent-failures>\n"
                    + "\n".join(failures_str)
                    + "\n</recent-failures>"
                )

        return "\n\n".join(parts)

    def run(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_iterations: int = 10,
        messages: list[dict] | None = None,
        session_id: str | None = None,
    ) -> tuple[str, list[dict]]:
        if not self.llm_provider:
            return f"Agent received: {prompt}", []

        self.cancelled = False
        self.loop_warning_count = 0
        self._prev_tool_sigs = None
        self.pause_event.set()

        if session_id:
            stored = self.memory.load_session(session_id)
            if stored and stored["messages"]:
                messages = list(stored["messages"])

        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        else:
            messages.append({"role": "user", "content": prompt})

        if session_id:
            self.memory.save_session(
                session_id, messages, project=self.project_path, status="active"
            )

        provider_name = "openai"
        if self.llm_provider:
            provider_class = self.llm_provider.__class__.__name__.lower()
            if "anthropic" in provider_class:
                provider_name = "anthropic"

        tools = self.tool_schemas(provider_name)
        injected_sys = self.build_system_prompt(system_prompt)

        for _ in range(max_iterations):
            if self.cancelled:
                if self.on_cancelled:
                    self.on_cancelled()
                return "Execution cancelled.", messages

            self.pause_event.wait()
            if self.on_paused:
                self.on_paused()

            if self.on_thinking:
                self.on_thinking()
            response = self.llm_provider.chat(
                messages=messages,
                tools=tools if tools else None,
                system_prompt=injected_sys,
            )

            if self.cancelled:
                if self.on_cancelled:
                    self.on_cancelled()
                return "Execution cancelled.", messages

            if response.tool_calls:
                current_sigs = sorted(
                    (tc.name, json.dumps(tc.arguments, sort_keys=True))
                    for tc in response.tool_calls
                )
                if (
                    self._prev_tool_sigs is not None
                    and current_sigs == self._prev_tool_sigs
                ):
                    self.loop_warning_count += 1
                    warning = (
                        f"[SYSTEM WARNING] The agent appears to be in a loop "
                        f"(repeated tool call #{self.loop_warning_count}). "
                        "Try a different approach or strategy."
                    )
                    if self.on_loop_detected:
                        self.on_loop_detected(self.loop_warning_count)
                    if self.loop_warning_count >= 3:
                        self.pause_event.clear()
                        messages.append(
                            {
                                "role": "assistant",
                                "content": "I detected a repeated execution pattern and have paused "
                                "to avoid an infinite loop. Please review and provide guidance.",
                            }
                        )
                        return "Auto-paused: loop detected.", messages
                    messages.append({"role": "system", "content": warning})
                else:
                    self.loop_warning_count = 0
                self._prev_tool_sigs = current_sigs

                for tc in response.tool_calls:
                    if self.on_tool_call:
                        self.on_tool_call(tc.name, tc.arguments)
                    result = self.execute_tool(tc.name, tc.arguments)
                    if self.on_tool_result:
                        self.on_tool_result(tc.name, result)
                    messages.append(
                        {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.name,
                                        "arguments": json.dumps(tc.arguments),
                                    },
                                }
                            ],
                        }
                    )
                    messages.append(
                        {"role": "tool", "tool_call_id": tc.id, "content": result}
                    )

                if session_id:
                    self.memory.save_session(
                        session_id, messages, project=self.project_path, status="active"
                    )
            else:
                self.loop_warning_count = 0
                self._prev_tool_sigs = None
                messages.append(
                    {"role": "assistant", "content": response.content or ""}
                )

                tc_count = sum(
                    len(msg.get("tool_calls") or [])
                    for msg in messages
                    if msg.get("role") == "assistant" and msg.get("tool_calls")
                )
                if self.background_review:
                    self.background_review.on_turn_end(
                        turn_count=1, tool_calls=tc_count, messages=messages
                    )

                if session_id:
                    self.memory.save_session(
                        session_id, messages, project=self.project_path, status="active"
                    )

                return response.content or "", messages

        messages.append({"role": "assistant", "content": "Max iterations reached."})

        tc_count = sum(
            len(msg.get("tool_calls") or [])
            for msg in messages
            if msg.get("role") == "assistant" and msg.get("tool_calls")
        )
        if self.background_review:
            self.background_review.on_turn_end(
                turn_count=1, tool_calls=tc_count, messages=messages
            )

        if session_id:
            self.memory.save_session(
                session_id, messages, project=self.project_path, status="active"
            )

        return "Max iterations reached.", messages
