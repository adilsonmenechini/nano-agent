from __future__ import annotations

import inspect
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from nanoagent.tool import Tool, py_to_json_schema
from nanoagent.registry import ToolRegistry
from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.skills.skill_storage import SkillStorage
from nanoagent.llm.base import StreamEvent
from nanoagent.agent.errors import ProviderRetryableError


class AgentState(Enum):
    IDLE = auto()
    THINKING = auto()
    EXECUTING_TOOLS = auto()
    AWAITING_INPUT = auto()
    ERROR = auto()


_VALID_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.IDLE: {AgentState.THINKING},
    AgentState.THINKING: {AgentState.EXECUTING_TOOLS, AgentState.AWAITING_INPUT, AgentState.IDLE, AgentState.ERROR},
    AgentState.EXECUTING_TOOLS: {AgentState.THINKING, AgentState.AWAITING_INPUT, AgentState.ERROR},
    AgentState.AWAITING_INPUT: {AgentState.IDLE},
    AgentState.ERROR: {AgentState.IDLE, AgentState.THINKING},
}


@dataclass
class StateTransition:
    from_state: AgentState
    to_state: AgentState
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


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

        # ── State machine ──────────────────────────────────────────────────
        self._state = AgentState.IDLE
        self._state_listeners: list[callable] = []

        # ── Execution control ──────────────────────────────────────────────
        self.cancelled = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.loop_warning_count = 0
        self._prev_tool_sigs: list[tuple[str, str]] | None = None

        # ── Callbacks ──────────────────────────────────────────────────────
        # on_state_change(transition) → called on every state transition
        # on_thinking()              → called before each LLM request
        # on_tool_call(name, args)   → called before a tool is executed
        # on_tool_result(name, res)  → called after a tool returns
        # on_skill_call(name, args)  → called before a skill is executed
        # on_skill_result(name, res) → called after a skill returns
        self.on_state_change: Any = None
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
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.retry_attempts = config.retry_attempts
        self.stream_enabled = config.stream
        self._config_providers = dict(config.providers) if config.providers else {}

        # Auto-load skills from DB
        try:
            from nanoagent.skills.loader import SkillsLoader, SkillContext
            ctx = SkillContext(tools=dict(self._tools.all()), memory=self.memory)
            db_skills = SkillsLoader.load_from_db(self.skill_storage, context=ctx)
            for name, wrapper in db_skills.items():
                self._skills[name] = wrapper
        except Exception:
            pass

        self.background_review = None
        if self.review_enabled:
            from nanoagent.memory.background_review import BackgroundReview

            self.background_review = BackgroundReview(
                self,
                nudge_interval=self.nudge_interval,
                nudge_tool_calls=self.nudge_tool_calls,
            )

    @property
    def state(self) -> AgentState:
        return self._state

    def add_state_listener(self, listener: callable) -> None:
        self._state_listeners.append(listener)

    def _transition(self, to_state: AgentState, reason: str = "", **metadata: object) -> None:
        from_state = self._state
        allowed = _VALID_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            from nanoagent.agent.errors import StateTransitionError
            raise StateTransitionError(
                f"Invalid transition: {from_state.name} -> {to_state.name}"
            )
        self._state = to_state
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            metadata=metadata,
        )
        if self.on_state_change:
            self.on_state_change(transition)
        for listener in self._state_listeners:
            listener(transition)

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
        query: str | None = None,
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

            # 4. Semantic memory retrieval if query provided
            if query and hasattr(self.memory, "semantic_search"):
                try:
                    semantic_entries = self.memory.semantic_search(
                        query, target="memory", limit=5
                    )
                    if semantic_entries:
                        from nanoagent.agent.context import select_top_memories
                        texts = [e.content for e in semantic_entries]
                        selected = select_top_memories(texts, max_tokens=1000)
                        if selected:
                            parts.append(
                                "<semantic-memory>\n"
                                + "\n".join(f"- {t}" for t in selected)
                                + "\n</semantic-memory>"
                            )
                except Exception:
                    pass

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

    def _chat_with_retry(self, *args, **kwargs):
        attempts_left = max(getattr(self, "retry_attempts", None) or 3, 1)
        last_exc = None
        for attempt in range(attempts_left):
            try:
                return self.llm_provider.chat(*args, **kwargs)
            except ProviderRetryableError as e:
                last_exc = e
                if attempt < attempts_left - 1:
                    wait = 1.0 * (2 ** attempt)
                    import time as _time
                    _time.sleep(wait)
                    continue
                raise
            except Exception:
                raise
        raise last_exc  # type: ignore[misc]

    def run(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_iterations: int = 10,
        messages: list[dict] | None = None,
        session_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
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
        injected_sys = self.build_system_prompt(system_prompt, query=prompt)

        self._transition(AgentState.THINKING, "received user input")

        for _ in range(max_iterations):
            if self.cancelled:
                self._transition(AgentState.IDLE, "cancelled")
                if self.on_cancelled:
                    self.on_cancelled()
                return "Execution cancelled.", messages

            self.pause_event.wait()
            if self.on_paused:
                self.on_paused()

            if self.on_thinking:
                self.on_thinking()
            chat_kwargs = {}
            if max_tokens is not None:
                chat_kwargs["max_tokens"] = max_tokens
            if temperature is not None:
                chat_kwargs["temperature"] = temperature
            try:
                response = self._chat_with_retry(
                    messages=messages,
                    tools=tools if tools else None,
                    system_prompt=injected_sys,
                    **chat_kwargs,
                )
            except Exception as exc:
                self._transition(AgentState.ERROR, f"LLM call failed: {exc}")
                raise

            if self.cancelled:
                self._transition(AgentState.IDLE, "cancelled")
                if self.on_cancelled:
                    self.on_cancelled()
                return "Execution cancelled.", messages

            if response.tool_calls:
                self._transition(AgentState.EXECUTING_TOOLS, "tool calls received")

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
                        self._transition(AgentState.AWAITING_INPUT, "loop detected")
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

                if len(response.tool_calls) > 1:
                    tc_pairs = [(tc.name, tc.arguments) for tc in response.tool_calls]
                    results = self._tools.execute_parallel(tc_pairs)
                    for i, tc in enumerate(response.tool_calls):
                        if self.on_tool_call:
                            self.on_tool_call(tc.name, tc.arguments)
                        if self.on_tool_result:
                            self.on_tool_result(tc.name, results[i])
                        messages.append({
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }],
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": results[i],
                        })
                else:
                    for tc in response.tool_calls:
                        if self.on_tool_call:
                            self.on_tool_call(tc.name, tc.arguments)
                        result = self.execute_tool(tc.name, tc.arguments)
                        if self.on_tool_result:
                            self.on_tool_result(tc.name, result)
                        messages.append({
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }],
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        })

                if session_id:
                    self.memory.save_session(
                        session_id, messages, project=self.project_path, status="active"
                    )

                self._transition(AgentState.THINKING, "tool results ready, continuing")
            else:
                self.loop_warning_count = 0
                self._prev_tool_sigs = None
                self._transition(AgentState.IDLE, "response ready")
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

    def run_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_iterations: int = 10,
        messages: list[dict] | None = None,
        session_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        if not self.llm_provider:
            yield StreamEvent(type="content", delta=f"Agent received: {prompt}")
            yield StreamEvent(type="done")
            return

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
        injected_sys = self.build_system_prompt(system_prompt, query=prompt)

        self._transition(AgentState.THINKING, "received user input (streaming)")

        for _ in range(max_iterations):
            if self.cancelled:
                self._transition(AgentState.IDLE, "cancelled")
                if self.on_cancelled:
                    self.on_cancelled()
                yield StreamEvent(type="content", delta="Execution cancelled.")
                yield StreamEvent(type="done")
                return

            self.pause_event.wait()
            if self.on_paused:
                self.on_paused()
            if self.on_thinking:
                self.on_thinking()

            chat_kwargs = {}
            if max_tokens is not None:
                chat_kwargs["max_tokens"] = max_tokens
            if temperature is not None:
                chat_kwargs["temperature"] = temperature

            try:
                stream = self._chat_with_retry(
                    messages=messages,
                    tools=tools if tools else None,
                    system_prompt=injected_sys,
                    stream=True,
                    **chat_kwargs,
                )
            except Exception as exc:
                self._transition(AgentState.ERROR, f"LLM call failed: {exc}")
                yield StreamEvent(type="content", delta=f"Error: {exc}")
                yield StreamEvent(type="done")
                return

            content_parts: list[str] = []
            _tool_calls_data: list[dict[str, Any]] = []
            for event in stream:
                if self.cancelled:
                    self._transition(AgentState.IDLE, "cancelled")
                    yield StreamEvent(type="done")
                    return
                if event.type == "content":
                    content_parts.append(event.delta or "")
                    yield event
                elif event.type == "tool_call":
                    _tool_calls_data.append(event.delta or {})
                    yield event
                elif event.type == "done":
                    break

            content = "".join(content_parts)

            if _tool_calls_data:
                self._transition(AgentState.EXECUTING_TOOLS, "tool calls from stream")
                from nanoagent.llm.base import ToolCall as TCall

                tool_calls = [
                    TCall(
                        id=tc.get("id", ""),
                        name=tc.get("name", tc.get("function", {}).get("name", "")),
                        arguments=tc.get("arguments", tc.get("input", {})),
                    )
                    for tc in _tool_calls_data
                ]

                current_sigs = sorted(
                    (tc.name, json.dumps(tc.arguments, sort_keys=True))
                    for tc in tool_calls
                )
                if (
                    self._prev_tool_sigs is not None
                    and current_sigs == self._prev_tool_sigs
                ):
                    self.loop_warning_count += 1
                    if self.loop_warning_count >= 3:
                        self._transition(AgentState.AWAITING_INPUT, "loop detected")
                        yield StreamEvent(type="content", delta="Auto-paused: loop detected.")
                        yield StreamEvent(type="done")
                        return
                else:
                    self.loop_warning_count = 0
                self._prev_tool_sigs = current_sigs

                for tc in tool_calls:
                    if self.on_tool_call:
                        self.on_tool_call(tc.name, tc.arguments)
                    result = self.execute_tool(tc.name, tc.arguments)
                    if self.on_tool_result:
                        self.on_tool_result(tc.name, result)
                    messages.append({
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }],
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

                self._transition(AgentState.THINKING, "tool results ready")
            else:
                self._transition(AgentState.IDLE, "response ready")
                messages.append({"role": "assistant", "content": content})
                yield StreamEvent(type="done")
                return

        yield StreamEvent(type="content", delta="Max iterations reached.")
        yield StreamEvent(type="done")
